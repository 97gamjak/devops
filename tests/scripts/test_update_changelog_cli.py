"""Tests for update_changelog CLI script."""

from __future__ import annotations

import typing
from pathlib import Path
from unittest.mock import patch

from typer.testing import CliRunner

from devops.files.update_changelog import DevOpsChangelogError
from devops.scripts.update_changelog import update_changelog, update_changelogs

if typing.TYPE_CHECKING:
    from pathlib import Path as PathType

runner = CliRunner()


class TestUpdateChangelogCLI:
    """Tests for update_changelog Typer CLI command."""

    def test_update_changelog_command_exists(self) -> None:
        """Test that update_changelog command is registered."""
        result = runner.invoke(update_changelog, ["--help"])
        assert result.exit_code == 0
        assert "Update the changelog file" in result.stdout

    def test_update_changelog_with_changelog_path_argument(
        self, tmp_path: PathType
    ) -> None:
        """Test update_changelog command with changelog_path argument.

        Parameters
        ----------
        tmp_path: PathType
            Temporary path for creating test files.

        """
        # Create a test changelog file
        changelog_file = tmp_path / "TEST_CHANGELOG.md"
        changelog_file.write_text(
            "# Changelog\n\n## Next Release\n\n- Test change\n\n"
            "<!-- insertion marker -->\n"
        )

        with patch(
            "devops.scripts.update_changelog.update_changelog_func"
        ) as mock_update:
            mock_update.return_value = None

            result = runner.invoke(
                update_changelog, ["1.0.0", "--changelog-path", str(changelog_file)]
            )

            assert result.exit_code == 0
            # Should call update_changelog with the provided path
            assert mock_update.call_count == 1
            call_args = mock_update.call_args[0]
            assert call_args[0] == "1.0.0"
            # Should convert string to Path
            assert isinstance(call_args[1], Path)
            assert call_args[1] == Path(changelog_file)

    def test_update_changelog_uses_config_default_when_no_arg(self) -> None:
        """Test update_changelog uses config default when no changelog_path provided."""
        with (
            patch(
                "devops.scripts.update_changelog.update_changelog_func"
            ) as mock_update,
            patch("devops.scripts.update_changelog.config") as mock_config,
        ):
            mock_update.return_value = None
            mock_config.file.default_changelog_path = Path("/config/path/CHANGELOG.md")

            _result = runner.invoke(update_changelog, ["1.0.0"])

            # Should use the global config's default_changelog_path
            assert mock_update.call_count == 1
            call_args = mock_update.call_args[0]
            assert call_args[0] == "1.0.0"
            # The config returns a Path object
            assert call_args[1] == Path("/config/path/CHANGELOG.md")

    def test_update_changelog_converts_string_to_path(self, tmp_path: PathType) -> None:
        """Test that string input is properly handled for Path conversion.

        Parameters
        ----------
        tmp_path: PathType
            Temporary path for creating test files.

        """
        changelog_file = tmp_path / "CHANGELOG.md"
        changelog_file.write_text(
            "# Changelog\n\n## Next Release\n\n- Feature\n\n<!-- insertion marker -->\n"
        )

        with patch(
            "devops.scripts.update_changelog.update_changelog_func"
        ) as mock_update:
            mock_update.return_value = None

            # Pass as string
            result = runner.invoke(
                update_changelog, ["2.0.0", "--changelog-path", str(changelog_file)]
            )

            assert result.exit_code == 0
            assert mock_update.call_count == 1
            # Verify it's called with a Path object
            call_args = mock_update.call_args[0]
            assert isinstance(call_args[1], Path)
            assert call_args[1] == Path(changelog_file)

    def test_update_changelog_handles_error(self) -> None:
        """Test update_changelog command handles DevOpsChangelogError."""
        with (
            patch(
                "devops.scripts.update_changelog.update_changelog_func"
            ) as mock_update,
            patch("devops.scripts.update_changelog.config") as mock_config,
        ):
            mock_update.side_effect = DevOpsChangelogError("Test error")
            mock_config.file.default_changelog_path = Path("/default/CHANGELOG.md")

            result = runner.invoke(update_changelog, ["1.0.0"])

            assert result.exit_code == 1
            assert "Error updating changelog" in result.stdout

    def test_update_changelog_success_message(self, tmp_path: PathType) -> None:
        """Test that successful update shows correct message.

        Parameters
        ----------
        tmp_path: PathType
            Temporary path for creating test files.

        """
        changelog_file = tmp_path / "CHANGELOG.md"
        changelog_file.write_text(
            "# Changelog\n\n## Next Release\n\n- Change\n\n<!-- insertion marker -->\n"
        )

        with patch(
            "devops.scripts.update_changelog.update_changelog_func"
        ) as mock_update:
            mock_update.return_value = None

            result = runner.invoke(
                update_changelog, ["3.0.0", "--changelog-path", str(changelog_file)]
            )

            assert result.exit_code == 0
            assert "✅ CHANGELOG.md updated for version 3.0.0" in result.stdout


class TestUpdateChangelogsCLI:
    """Tests for update_changelogs Typer CLI command."""

    def test_update_changelogs_command_exists(self) -> None:
        """Test that update_changelogs command is registered."""
        result = runner.invoke(update_changelogs, ["--help"])
        assert result.exit_code == 0
        assert "Update multiple changelog files" in result.stdout

    def test_update_changelogs_with_multiple_explicit_paths(
        self, tmp_path: PathType
    ) -> None:
        """Test update_changelogs with multiple explicit changelog paths.

        Parameters
        ----------
        tmp_path: PathType
            Temporary path for creating test files.

        """
        # Create test changelog files
        changelog1 = tmp_path / "CHANGELOG1.md"
        changelog2 = tmp_path / "CHANGELOG2.md"

        with patch(
            "devops.scripts.update_changelog.update_changelog_func"
        ) as mock_update:
            mock_update.return_value = None

            result = runner.invoke(
                update_changelogs,
                [
                    "1.0.0",
                    "--changelog-paths",
                    str(changelog1),
                    "--changelog-paths",
                    str(changelog2),
                ],
            )

            assert result.exit_code == 0
            # Should call update_changelog_func twice, once for each path
            assert mock_update.call_count == 2

            # Check both calls
            first_call = mock_update.call_args_list[0]
            assert first_call[0][0] == "1.0.0"
            assert isinstance(first_call[0][1], Path)
            assert first_call[0][1] == Path(changelog1)

            second_call = mock_update.call_args_list[1]
            assert second_call[0][0] == "1.0.0"
            assert isinstance(second_call[0][1], Path)
            assert second_call[0][1] == Path(changelog2)

    def test_update_changelogs_uses_config_defaults(self) -> None:
        """Test update_changelogs uses config defaults when no paths provided."""
        with (
            patch(
                "devops.scripts.update_changelog.update_changelog_func"
            ) as mock_update,
            patch("devops.scripts.update_changelog.config") as mock_config,
        ):
            mock_update.return_value = None
            mock_config.file.changelog_paths = [
                Path("/config/CHANGELOG1.md"),
                Path("/config/CHANGELOG2.md"),
                Path("/config/CHANGELOG3.md"),
            ]

            result = runner.invoke(update_changelogs, ["2.0.0"])

            assert result.exit_code == 0
            # Should call update_changelog_func three times
            assert mock_update.call_count == 3

            # Verify all three config paths were used
            call_paths = [call[0][1] for call in mock_update.call_args_list]
            assert Path("/config/CHANGELOG1.md") in call_paths
            assert Path("/config/CHANGELOG2.md") in call_paths
            assert Path("/config/CHANGELOG3.md") in call_paths

    def test_update_changelogs_handles_partial_failures(
        self, tmp_path: PathType
    ) -> None:
        """Test update_changelogs handles partial failures correctly.

        Parameters
        ----------
        tmp_path: PathType
            Temporary path for creating test files.

        """
        changelog1 = tmp_path / "CHANGELOG1.md"
        changelog2 = tmp_path / "CHANGELOG2.md"
        changelog3 = tmp_path / "CHANGELOG3.md"

        def mock_update_side_effect(_version: str, path: Path) -> None:
            # Fail for the second changelog
            if path == Path(changelog2):
                msg = "Mock error for CHANGELOG2"
                raise DevOpsChangelogError(msg)

        with patch(
            "devops.scripts.update_changelog.update_changelog_func"
        ) as mock_update:
            mock_update.side_effect = mock_update_side_effect

            result = runner.invoke(
                update_changelogs,
                [
                    "1.0.0",
                    "--changelog-paths",
                    str(changelog1),
                    "--changelog-paths",
                    str(changelog2),
                    "--changelog-paths",
                    str(changelog3),
                ],
            )

            # Should exit with error code 1 due to failures
            assert result.exit_code == 1

            # Should have tried all three changelogs
            assert mock_update.call_count == 3

            # Check output contains success and error messages
            # Use 'in' check that accounts for potential line wrapping
            assert "✅" in result.stdout
            assert str(changelog1) in result.stdout
            assert "1.0.0" in result.stdout
            assert "❌ Error updating" in result.stdout
            assert str(changelog2) in result.stdout
            assert "Mock error for CHANGELOG2" in result.stdout
            assert str(changelog3) in result.stdout

    def test_update_changelogs_handles_all_failures(self, tmp_path: PathType) -> None:
        """Test update_changelogs when all updates fail.

        Parameters
        ----------
        tmp_path: PathType
            Temporary path for creating test files.

        """
        changelog1 = tmp_path / "CHANGELOG1.md"
        changelog2 = tmp_path / "CHANGELOG2.md"

        with patch(
            "devops.scripts.update_changelog.update_changelog_func"
        ) as mock_update:
            mock_update.side_effect = DevOpsChangelogError("Mock error")

            result = runner.invoke(
                update_changelogs,
                [
                    "1.0.0",
                    "--changelog-paths",
                    str(changelog1),
                    "--changelog-paths",
                    str(changelog2),
                ],
            )

            # Should exit with error code 1
            assert result.exit_code == 1

            # Should have tried both changelogs
            assert mock_update.call_count == 2

            # Both should show error messages
            assert "❌ Error updating" in result.stdout
            assert str(changelog1) in result.stdout
            assert str(changelog2) in result.stdout
            assert "Mock error" in result.stdout

    def test_update_changelogs_converts_strings_to_paths(
        self, tmp_path: PathType
    ) -> None:
        """Test that string paths are properly converted to Path objects.

        Parameters
        ----------
        tmp_path: PathType
            Temporary path for creating test files.

        """
        changelog1 = tmp_path / "CHANGELOG1.md"
        changelog2 = tmp_path / "CHANGELOG2.md"

        with patch(
            "devops.scripts.update_changelog.update_changelog_func"
        ) as mock_update:
            mock_update.return_value = None

            result = runner.invoke(
                update_changelogs,
                [
                    "1.0.0",
                    "--changelog-paths",
                    str(changelog1),
                    "--changelog-paths",
                    str(changelog2),
                ],
            )

            assert result.exit_code == 0
            assert mock_update.call_count == 2

            # Verify both calls received Path objects
            for call in mock_update.call_args_list:
                assert isinstance(call[0][1], Path)

    def test_update_changelogs_success_messages(self, tmp_path: PathType) -> None:
        """Test that successful updates show correct messages for each file.

        Parameters
        ----------
        tmp_path: PathType
            Temporary path for creating test files.

        """
        changelog1 = tmp_path / "PROJECT_CHANGELOG.md"
        changelog2 = tmp_path / "API_CHANGELOG.md"

        with patch(
            "devops.scripts.update_changelog.update_changelog_func"
        ) as mock_update:
            mock_update.return_value = None

            result = runner.invoke(
                update_changelogs,
                [
                    "3.5.0",
                    "--changelog-paths",
                    str(changelog1),
                    "--changelog-paths",
                    str(changelog2),
                ],
            )

            assert result.exit_code == 0

            # Should show success message for each changelog with specific filename
            assert "✅" in result.stdout
            assert "PROJECT_CHANGELOG" in result.stdout
            assert "API_CHANGELOG" in result.stdout
            assert "3.5.0" in result.stdout
