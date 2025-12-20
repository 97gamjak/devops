"""Unit tests for changelog update functionality in mstd checks."""

from datetime import UTC, datetime

import pytest

from devops.config import Constants
from devops.files.files import MSTDFileNotFoundError
from devops.files.update_changelog import (
    __CHANGELOG_INSERTION_MARKER__,
    DevOpsChangelogError,
    update_changelog,
)

owner_url = Constants.github.github_default_owner_url


class TestDevOpsChangelogError:
    """Tests for DevOpsChangelogError exception class."""

    def test_changelog_error_message(self) -> None:
        """Test that DevOpsChangelogError formats message correctly."""
        error = DevOpsChangelogError("test error message")
        assert str(error) == "DevOpsChangelogError: test error message"
        assert error.message == "test error message"

    def test_changelog_error_is_exception(self) -> None:
        """Test that DevOpsChangelogError is a proper exception."""
        error = DevOpsChangelogError("test")
        assert isinstance(error, Exception)


class TestUpdateChangelog:
    """Tests for update_changelog function."""

    def test_update_changelog_success(self, tmp_path: pytest.TempdirFactory) -> None:
        """Test successful changelog update with new version.

        Parameters
        ----------
        tmp_path : pytest.TempdirFactory
            Temporary directory for test files.

        """
        changelog = tmp_path / "CHANGELOG.md"
        changelog.write_text(
            "# Changelog\n"
            "\n"
            "## Next Release\n"
            "\n"
            "- Some change\n"
            "\n"
            "<!-- insertion marker -->\n"
            "\n"
            f"## [1.0.0]({owner_url}/releases/tag/1.0.0) - 2024-01-01\n"
            "\n"
            "- Initial release\n"
        )

        update_changelog("1.1.0", changelog)

        content = changelog.read_text()
        assert f"## [1.1.0]({owner_url}/releases/tag/1.1.0)" in content
        assert "## Next Release" in content
        # Marker should be after Next Release now
        next_release_pos = content.find("## Next Release")
        marker_pos = content.find(__CHANGELOG_INSERTION_MARKER__)
        new_version_pos = content.find("## [1.1.0]")
        assert next_release_pos < marker_pos < new_version_pos

    def test_update_changelog_with_date(self, tmp_path: pytest.TempdirFactory) -> None:
        """Test that changelog entry includes today's date.

        Parameters
        ----------
        tmp_path : pytest.TempdirFactory
            Temporary directory for test files.

        """
        changelog = tmp_path / "CHANGELOG.md"
        changelog.write_text(
            "# Changelog\n"
            "\n"
            "## Next Release\n"
            "\n"
            "- New feature\n"
            "\n"
            "<!-- insertion marker -->\n"
        )

        update_changelog("2.0.0", changelog)

        content = changelog.read_text()
        today = datetime.now(tz=UTC).date().isoformat()
        assert f"## [2.0.0]({owner_url}/releases/tag/2.0.0) - {today}" in content

    def test_update_changelog_file_not_found(
        self, tmp_path: pytest.TempdirFactory
    ) -> None:
        """Test that MSTDFileNotFoundError is raised when file doesn't exist.

        Parameters
        ----------
        tmp_path : pytest.TempdirFactory
            Temporary directory for test files.

        """
        non_existent = tmp_path / "does_not_exist.md"

        with pytest.raises(MSTDFileNotFoundError) as exc_info:
            update_changelog("1.0.0", non_existent)

        assert exc_info.value.filepath == non_existent

    def test_update_changelog_missing_next_release(
        self, tmp_path: pytest.TempdirFactory
    ) -> None:
        """Test that DevOpsChangelogError is raised when Next Release marker missing.

        Parameters
        ----------
        tmp_path : pytest.TempdirFactory
            Temporary directory for test files.

        """
        changelog = tmp_path / "CHANGELOG.md"
        changelog.write_text(
            "# Changelog\n"
            "\n"
            f"## [1.0.0]({owner_url}/releases/tag/1.0.0) - 2024-01-01\n"
            "\n"
            "- Initial release\n"
        )

        with pytest.raises(DevOpsChangelogError) as exc_info:
            update_changelog("1.1.0", changelog)

        assert "Next Release" in exc_info.value.message

    def test_update_changelog_removes_old_marker(
        self, tmp_path: pytest.TempdirFactory
    ) -> None:
        """Test that old insertion marker is removed and new one is placed.

        Parameters
        ----------
        tmp_path : pytest.TempdirFactory
            Temporary directory for test files.

        """
        changelog = tmp_path / "CHANGELOG.md"
        changelog.write_text(
            "# Changelog\n"
            "\n"
            "## Next Release\n"
            "\n"
            "- New change\n"
            "\n"
            f"## [1.0.0]({owner_url}/releases/tag/1.0.0) - 2024-01-01\n"
            "\n"
            "<!-- insertion marker -->\n"
            "\n"
            f"## [0.9.0]({owner_url}/releases/tag/0.9.0) - 2023-12-01\n"
        )

        update_changelog("1.1.0", changelog)

        content = changelog.read_text()
        # Should have exactly one marker
        assert content.count(__CHANGELOG_INSERTION_MARKER__) == 1
        # Marker should be right after Next Release section heading
        next_release_pos = content.find("## Next Release")
        marker_pos = content.find(__CHANGELOG_INSERTION_MARKER__)
        assert next_release_pos < marker_pos

    def test_update_changelog_no_existing_marker(
        self, tmp_path: pytest.TempdirFactory
    ) -> None:
        """Test changelog update when no insertion marker exists.

        Parameters
        ----------
        tmp_path : pytest.TempdirFactory
            Temporary directory for test files.

        """
        changelog = tmp_path / "CHANGELOG.md"
        changelog.write_text(
            "# Changelog\n"
            "\n"
            "## Next Release\n"
            "\n"
            "- Feature A\n"
            "\n"
            f"## [1.0.0]({owner_url}/releases/tag/1.0.0) - 2024-01-01\n"
        )

        update_changelog("1.1.0", changelog)

        content = changelog.read_text()
        assert __CHANGELOG_INSERTION_MARKER__ in content
        assert "## [1.1.0]" in content

    def test_update_changelog_preserves_content(
        self, tmp_path: pytest.TempdirFactory
    ) -> None:
        """Test that changelog update preserves existing content.

        Parameters
        ----------
        tmp_path : pytest.TempdirFactory
            Temporary directory for test files.

        """
        changelog = tmp_path / "CHANGELOG.md"
        original_content = (
            "# Changelog\n"
            "\n"
            "All notable changes to this project.\n"
            "\n"
            "## Next Release\n"
            "\n"
            "### Added\n"
            "- New feature\n"
            "\n"
            "### Fixed\n"
            "- Bug fix\n"
            "\n"
            "<!-- insertion marker -->\n"
            "\n"
            f"## [1.0.0]({owner_url}/releases/tag/1.0.0) - 2024-01-01\n"
            "\n"
            "### Added\n"
            "- Initial release\n"
        )
        changelog.write_text(original_content)

        update_changelog("1.1.0", changelog)

        content = changelog.read_text()
        # Check original sections are preserved
        assert "# Changelog" in content
        assert "All notable changes to this project." in content
        assert "### Added" in content
        assert "- New feature" in content
        assert "### Fixed" in content
        assert "- Bug fix" in content
        assert "- Initial release" in content
        assert "## [1.0.0]" in content

    def test_update_changelog_next_release_regex_variations(
        self, tmp_path: pytest.TempdirFactory
    ) -> None:
        """Test that regex matches various Next Release formats.

        Parameters
        ----------
        tmp_path : pytest.TempdirFactory
            Temporary directory for test files.

        """
        # Test with extra spaces
        changelog = tmp_path / "CHANGELOG.md"
        changelog.write_text(
            "# Changelog\n"
            "\n"
            "##   Next Release\n"
            "\n"
            "- Change\n"
            "\n"
            "<!-- insertion marker -->\n"
        )

        update_changelog("1.0.0", changelog)

        content = changelog.read_text()
        assert "## [1.0.0]" in content

    def test_update_changelog_empty_next_release(
        self, tmp_path: pytest.TempdirFactory
    ) -> None:
        """Test changelog update when Next Release section is empty.

        Parameters
        ----------
        tmp_path : pytest.TempdirFactory
            Temporary directory for test files.

        """
        changelog = tmp_path / "CHANGELOG.md"
        changelog.write_text(
            "# Changelog\n"
            "\n"
            "## Next Release\n"
            "\n"
            "<!-- insertion marker -->\n"
            "\n"
            f"## [1.0.0]({owner_url}/releases/tag/1.0.0) - 2024-01-01\n"
        )

        update_changelog("1.1.0", changelog)

        content = changelog.read_text()
        assert "## [1.1.0]" in content
        assert "## [1.0.0]" in content
