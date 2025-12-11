"""Unit tests for changelog update functionality in mstd checks."""

from datetime import UTC, datetime
from unittest.mock import patch

import pytest

from devops.files.files import MSTDFileNotFoundError
from devops.files.update_changelog import (
    MSTDChangelogError,
    __CHANGELOG_INSERTION_MARKER__,
    update_changelog,
)


class TestMSTDChangelogError:
    """Tests for MSTDChangelogError exception class."""

    def test_changelog_error_message(self):
        """Test that MSTDChangelogError formats message correctly."""
        error = MSTDChangelogError("test error message")
        assert str(error) == "MSTDChangelogError: test error message"
        assert error.message == "test error message"

    def test_changelog_error_is_exception(self):
        """Test that MSTDChangelogError is a proper exception."""
        error = MSTDChangelogError("test")
        assert isinstance(error, Exception)


class TestUpdateChangelog:
    """Tests for update_changelog function."""

    @patch("devops.files.update_changelog.get_github_repo")
    def test_update_changelog_success(self, mock_get_repo, tmp_path):
        """Test successful changelog update with new version."""
        mock_get_repo.return_value = "https://github.com/test/repo"

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
            "## [1.0.0](https://github.com/test/repo/releases/tag/1.0.0) - 2024-01-01\n"
            "\n"
            "- Initial release\n"
        )

        update_changelog("1.1.0", changelog)

        content = changelog.read_text()
        assert "## [1.1.0](https://github.com/test/repo/releases/tag/1.1.0)" in content
        assert "## Next Release" in content
        # Marker should be after Next Release now
        next_release_pos = content.find("## Next Release")
        marker_pos = content.find(__CHANGELOG_INSERTION_MARKER__)
        new_version_pos = content.find("## [1.1.0]")
        assert next_release_pos < marker_pos < new_version_pos

    @patch("devops.files.update_changelog.get_github_repo")
    def test_update_changelog_with_date(self, mock_get_repo, tmp_path):
        """Test that changelog entry includes today's date."""
        mock_get_repo.return_value = "https://github.com/test/repo"

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
        assert f"## [2.0.0](https://github.com/test/repo/releases/tag/2.0.0) - {
            today}" in content

    def test_update_changelog_file_not_found(self, tmp_path):
        """Test that MSTDFileNotFoundError is raised when file doesn't exist."""
        non_existent = tmp_path / "does_not_exist.md"

        with pytest.raises(MSTDFileNotFoundError) as exc_info:
            update_changelog("1.0.0", non_existent)

        assert exc_info.value.filepath == non_existent

    @patch("devops.files.update_changelog.get_github_repo")
    def test_update_changelog_missing_next_release(self, mock_get_repo, tmp_path):
        """Test that MSTDChangelogError is raised when Next Release marker missing."""
        mock_get_repo.return_value = "https://github.com/test/repo"

        changelog = tmp_path / "CHANGELOG.md"
        changelog.write_text(
            "# Changelog\n"
            "\n"
            "## [1.0.0](https://github.com/test/repo/releases/tag/1.0.0) - 2024-01-01\n"
            "\n"
            "- Initial release\n"
        )

        with pytest.raises(MSTDChangelogError) as exc_info:
            update_changelog("1.1.0", changelog)

        assert "Next Release" in exc_info.value.message

    @patch("devops.files.update_changelog.get_github_repo")
    def test_update_changelog_removes_old_marker(self, mock_get_repo, tmp_path):
        """Test that old insertion marker is removed and new one is placed."""
        mock_get_repo.return_value = "https://github.com/test/repo"

        changelog = tmp_path / "CHANGELOG.md"
        changelog.write_text(
            "# Changelog\n"
            "\n"
            "## Next Release\n"
            "\n"
            "- New change\n"
            "\n"
            "## [1.0.0](https://github.com/test/repo/releases/tag/1.0.0) - 2024-01-01\n"
            "\n"
            "<!-- insertion marker -->\n"
            "\n"
            "## [0.9.0](https://github.com/test/repo/releases/tag/0.9.0) - 2023-12-01\n"
        )

        update_changelog("1.1.0", changelog)

        content = changelog.read_text()
        # Should have exactly one marker
        assert content.count(__CHANGELOG_INSERTION_MARKER__) == 1
        # Marker should be right after Next Release section heading
        next_release_pos = content.find("## Next Release")
        marker_pos = content.find(__CHANGELOG_INSERTION_MARKER__)
        assert next_release_pos < marker_pos

    @patch("devops.files.update_changelog.get_github_repo")
    def test_update_changelog_no_existing_marker(self, mock_get_repo, tmp_path):
        """Test changelog update when no insertion marker exists."""
        mock_get_repo.return_value = "https://github.com/test/repo"

        changelog = tmp_path / "CHANGELOG.md"
        changelog.write_text(
            "# Changelog\n"
            "\n"
            "## Next Release\n"
            "\n"
            "- Feature A\n"
            "\n"
            "## [1.0.0](https://github.com/test/repo/releases/tag/1.0.0) - 2024-01-01\n"
        )

        update_changelog("1.1.0", changelog)

        content = changelog.read_text()
        assert __CHANGELOG_INSERTION_MARKER__ in content
        assert "## [1.1.0]" in content

    @patch("devops.files.update_changelog.get_github_repo")
    def test_update_changelog_preserves_content(self, mock_get_repo, tmp_path):
        """Test that changelog update preserves existing content."""
        mock_get_repo.return_value = "https://github.com/test/repo"

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
            "## [1.0.0](https://github.com/test/repo/releases/tag/1.0.0) - 2024-01-01\n"
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

    @patch("devops.files.update_changelog.get_github_repo")
    def test_update_changelog_next_release_regex_variations(
        self, mock_get_repo, tmp_path
    ):
        """Test that regex matches various Next Release formats."""
        mock_get_repo.return_value = "https://github.com/test/repo"

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

    @patch("devops.files.update_changelog.get_github_repo")
    def test_update_changelog_empty_next_release(self, mock_get_repo, tmp_path):
        """Test changelog update when Next Release section is empty."""
        mock_get_repo.return_value = "https://github.com/test/repo"

        changelog = tmp_path / "CHANGELOG.md"
        changelog.write_text(
            "# Changelog\n"
            "\n"
            "## Next Release\n"
            "\n"
            "<!-- insertion marker -->\n"
            "\n"
            "## [1.0.0](https://github.com/test/repo/releases/tag/1.0.0) - 2024-01-01\n"
        )

        update_changelog("1.1.0", changelog)

        content = changelog.read_text()
        assert "## [1.1.0]" in content
        assert "## [1.0.0]" in content
