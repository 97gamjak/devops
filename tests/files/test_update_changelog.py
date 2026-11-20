"""Unit tests for changelog update functionality in mstd checks."""

import subprocess
from datetime import UTC, datetime
from pathlib import Path

import pytest

from devops.files.files import DevOpsFileNotFoundError
from devops.files.update_changelog import (
    __CHANGELOG_INSERTION_MARKER__,
    DevOpsChangelogError,
    get_repo_url,
    update_changelog,
)

owner_url = "https://github.com/owner/repo"


@pytest.fixture(autouse=True)
def github_repository(monkeypatch: pytest.MonkeyPatch) -> None:
    """Set the repository like GitHub Actions does.

    Parameters
    ----------
    monkeypatch : pytest.MonkeyPatch
        Fixture used to set the environment.

    """
    monkeypatch.setenv("GITHUB_REPOSITORY", "owner/repo")
    monkeypatch.setenv("GITHUB_SERVER_URL", "https://github.com")


def _git_repo(path: Path, monkeypatch: pytest.MonkeyPatch, remote: str | None) -> None:
    subprocess.run(["git", "init", "-q", str(path)], check=True)  # noqa: S603
    if remote is not None:
        subprocess.run(  # noqa: S603
            ["git", "-C", str(path), "remote", "add", "origin", remote], check=True
        )
    monkeypatch.delenv("GITHUB_REPOSITORY")
    monkeypatch.chdir(path)


class TestGetRepoUrl:
    """Tests for get_repo_url."""

    def test_from_environment(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that GITHUB_SERVER_URL and GITHUB_REPOSITORY are used.

        Parameters
        ----------
        monkeypatch : pytest.MonkeyPatch
            Fixture used to set the environment.

        """
        monkeypatch.setenv("GITHUB_SERVER_URL", "https://ghe.example/")
        assert get_repo_url() == "https://ghe.example/owner/repo"

    def test_server_defaults_to_github(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that github.com is used without GITHUB_SERVER_URL.

        Parameters
        ----------
        monkeypatch : pytest.MonkeyPatch
            Fixture used to set the environment.

        """
        monkeypatch.delenv("GITHUB_SERVER_URL")
        assert get_repo_url() == owner_url

    @pytest.mark.parametrize(
        "remote",
        [
            "git@github.com:MolarVerse/devops.git",
            "https://github.com/MolarVerse/devops",
            "https://github.com/MolarVerse/devops.git",
            "ssh://git@github.com/MolarVerse/devops.git",
        ],
    )
    def test_from_origin(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, remote: str
    ) -> None:
        """Test that the origin remote is used outside GitHub Actions.

        Parameters
        ----------
        tmp_path : Path
            Temporary directory for the repository.
        monkeypatch : pytest.MonkeyPatch
            Fixture used to set the environment.
        remote : str
            The origin URL.

        """
        _git_repo(tmp_path, monkeypatch, remote)
        assert get_repo_url() == "https://github.com/MolarVerse/devops"

    def test_no_origin(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that a missing origin is an error.

        Parameters
        ----------
        tmp_path : Path
            Temporary directory for the repository.
        monkeypatch : pytest.MonkeyPatch
            Fixture used to set the environment.

        """
        _git_repo(tmp_path, monkeypatch, None)
        with pytest.raises(DevOpsChangelogError, match="GITHUB_REPOSITORY"):
            get_repo_url()

    def test_origin_not_on_github(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that a non-GitHub origin is an error.

        Parameters
        ----------
        tmp_path : Path
            Temporary directory for the repository.
        monkeypatch : pytest.MonkeyPatch
            Fixture used to set the environment.

        """
        _git_repo(tmp_path, monkeypatch, "https://gitlab.com/owner/repo.git")
        with pytest.raises(DevOpsChangelogError, match="not a GitHub remote"):
            get_repo_url()


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

    def test_update_changelog_explicit_repo_url(self, tmp_path: Path) -> None:
        """Test that an explicit repo_url is used for the link.

        Parameters
        ----------
        tmp_path : Path
            Temporary directory for test files.

        """
        changelog = tmp_path / "CHANGELOG.md"
        changelog.write_text("## Next Release\n\n<!-- insertion marker -->\n")

        update_changelog("1.0.0", changelog, "https://github.com/MolarVerse/PQ")

        assert (
            "## [1.0.0](https://github.com/MolarVerse/PQ/releases/tag/1.0.0)"
            in changelog.read_text()
        )

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
        """Test that DevOpsFileNotFoundError is raised when file doesn't exist.

        Parameters
        ----------
        tmp_path : pytest.TempdirFactory
            Temporary directory for test files.

        """
        non_existent = tmp_path / "does_not_exist.md"

        with pytest.raises(DevOpsFileNotFoundError) as exc_info:
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
