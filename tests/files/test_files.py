"""Unit tests for file-related functionality in mstd checks."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from devops.files import FileType, GitRefError, get_changed_files


def test_all_types() -> None:
    """Test that FileType.all_types() returns the expected set of file types."""
    expected_types = {
        FileType.CPPHeader,
        FileType.CPPSource,
        FileType.UNKNOWN,
        FileType.CMakeLists,
    }

    actual_types = FileType.all_types()

    assert actual_types == expected_types


def _git(repo: Path, *args: str) -> str:
    """Run a git command in ``repo`` and return stdout."""
    return subprocess.run(  # noqa: S603
        ["git", "-c", "user.name=t", "-c", "user.email=t@t", *args],
        cwd=repo,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()


@pytest.fixture
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Create a git repo with a ``main`` commit and cwd set to it.

    Returns
    -------
    Path
        The repository root.

    """
    _git(tmp_path, "init", "-q", "-b", "main")
    (tmp_path / "old.cpp").write_text("int a;\n")
    (tmp_path / "gone.cpp").write_text("int g;\n")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-q", "-m", "base")
    monkeypatch.chdir(tmp_path)
    return tmp_path


class TestGetChangedFiles:
    """Tests for get_changed_files."""

    def test_branch_name_returns_branch_changes(self, repo: Path) -> None:
        """Files changed on a feature branch are reported against its base."""
        _git(repo, "checkout", "-q", "-b", "feature")
        (repo / "new.cpp").write_text("int b;\n")
        (repo / "old.cpp").write_text("int a2;\n")
        (repo / "gone.cpp").unlink()
        _git(repo, "add", "-A")
        _git(repo, "commit", "-q", "-m", "change")

        assert sorted(get_changed_files("main")) == [Path("new.cpp"), Path("old.cpp")]

    def test_merge_base_ignores_changes_on_base_branch(self, repo: Path) -> None:
        """Commits added to the base branch after branching are not reported."""
        _git(repo, "checkout", "-q", "-b", "feature")
        (repo / "feat.cpp").write_text("int f;\n")
        _git(repo, "add", "-A")
        _git(repo, "commit", "-q", "-m", "feat")
        _git(repo, "checkout", "-q", "main")
        (repo / "main_only.cpp").write_text("int m;\n")
        _git(repo, "add", "-A")
        _git(repo, "commit", "-q", "-m", "main change")
        _git(repo, "checkout", "-q", "feature")

        assert get_changed_files("main") == [Path("feat.cpp")]

    def test_commit_hash_and_uncommitted_changes(self, repo: Path) -> None:
        """A commit hash works and tracked uncommitted edits are included."""
        base = _git(repo, "rev-parse", "HEAD")
        (repo / "second.cpp").write_text("int s;\n")
        _git(repo, "add", "-A")
        _git(repo, "commit", "-q", "-m", "second")
        (repo / "old.cpp").write_text("int dirty;\n")

        assert sorted(get_changed_files(base)) == [Path("old.cpp"), Path("second.cpp")]

    def test_paths_relative_to_cwd(
        self, repo: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Paths are relative to the cwd and limited to it."""
        (repo / "sub").mkdir()
        (repo / "sub" / "x.cpp").write_text("int x;\n")
        (repo / "top.cpp").write_text("int t;\n")
        _git(repo, "add", "-A")
        monkeypatch.chdir(repo / "sub")

        assert get_changed_files("HEAD") == [Path("x.cpp")]

    def test_invalid_ref_raises(self, repo: Path) -> None:  # noqa: ARG002
        """An unknown ref raises GitRefError."""
        with pytest.raises(GitRefError, match="does-not-exist"):
            get_changed_files("does-not-exist")

    def test_option_like_ref_raises(self, repo: Path) -> None:
        """A ref that looks like a git option is rejected, not interpreted."""
        with pytest.raises(GitRefError):
            get_changed_files("--output=evil")
        assert not (repo / "evil").exists()
