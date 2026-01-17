"""Tests for update_changelog CLI script."""

from __future__ import annotations

import typing
from pathlib import Path
from unittest.mock import patch

from typer.testing import CliRunner

from devops.scripts.update_changelog import app

if typing.TYPE_CHECKING:
    from pathlib import Path as PathType

runner = CliRunner()


class TestUpdateChangelogCLI:
    """Tests for update_changelog Typer CLI command."""

    def test_update_changelog_command_exists(self) -> None:
        """Test that update_changelog command is registered."""
        result = runner.invoke(app, ["--help"])
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
            "devops.scripts.update_changelog.update_changelog.update_changelog"
        ) as mock_update:
            mock_update.return_value = None

            result = runner.invoke(
                app, ["1.0.0", "--changelog-path", str(changelog_file)]
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
                "devops.scripts.update_changelog.update_changelog.update_changelog"
            ) as mock_update,
            patch("devops.scripts.update_changelog.config") as mock_config,
        ):
            mock_update.return_value = None
            mock_config.file.default_changelog_path = Path("/config/path/CHANGELOG.md")

            result = runner.invoke(app, ["1.0.0"])

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
            "# Changelog\n\n## Next Release\n\n- Feature\n\n"
            "<!-- insertion marker -->\n"
        )

        with patch(
            "devops.scripts.update_changelog.update_changelog.update_changelog"
        ) as mock_update:
            mock_update.return_value = None

            # Pass as string
            result = runner.invoke(
                app, ["2.0.0", "--changelog-path", str(changelog_file)]
            )

            assert result.exit_code == 0
            assert mock_update.call_count == 1
            # Verify it's called with a Path object
            call_args = mock_update.call_args[0]
            assert isinstance(call_args[1], Path)
            assert call_args[1] == Path(changelog_file)

    def test_update_changelog_handles_error(self) -> None:
        """Test update_changelog command handles DevOpsChangelogError."""
        from devops.files.update_changelog import DevOpsChangelogError

        with (
            patch(
                "devops.scripts.update_changelog.update_changelog.update_changelog"
            ) as mock_update,
            patch("devops.scripts.update_changelog.config") as mock_config,
        ):
            mock_update.side_effect = DevOpsChangelogError("Test error")
            mock_config.file.default_changelog_path = Path("/default/CHANGELOG.md")

            result = runner.invoke(app, ["1.0.0"])

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
            "# Changelog\n\n## Next Release\n\n- Change\n\n"
            "<!-- insertion marker -->\n"
        )

        with patch(
            "devops.scripts.update_changelog.update_changelog.update_changelog"
        ) as mock_update:
            mock_update.return_value = None

            result = runner.invoke(
                app, ["3.0.0", "--changelog-path", str(changelog_file)]
            )

            assert result.exit_code == 0
            assert "✅ CHANGELOG.md updated for version 3.0.0" in result.stdout
