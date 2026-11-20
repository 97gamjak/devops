"""Shared fixtures: a local repository with a bare remote, and a fake GitHub."""

from __future__ import annotations

import os
import subprocess
import typing
from dataclasses import dataclass, field

import pytest

if typing.TYPE_CHECKING:
    from pathlib import Path
    from typing import Any


@dataclass
class ReleaseRepository:
    """A Git repository with a bare ``origin``; no network or user config."""

    root: Path
    remote: Path
    branch: Path
    commit: str = ""
    tree: str = ""

    def git(
        self, *arguments: str, stdin: str | None = None, remote: bool = False
    ) -> str:
        """Run Git in the clone or the bare remote and return its output.

        Parameters
        ----------
        *arguments: str
            The Git arguments.
        stdin: str | None
            Standard input for the command.
        remote: bool
            Run in the bare remote instead of the clone.

        Returns
        -------
        str
            The stripped standard output.

        """
        return subprocess.run(  # noqa: S603 - no shell, test git commands
            ["git", "-C", str(self.remote if remote else self.branch), *arguments],
            input=stdin,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()

    def new_commit(self, message: str, parent: str | None = None) -> str:
        """Create a commit with an empty tree without changing HEAD.

        Parameters
        ----------
        message: str
            The commit message.
        parent: str | None
            The parent commit, or None for a root commit.

        Returns
        -------
        str
            The new commit SHA.

        """
        arguments = ["commit-tree", self.tree]
        if parent:
            arguments += ["-p", parent]
        return self.git(*arguments, stdin=f"{message}\n")

    def tag(
        self, version: str, commit: str | None = None, *, annotated: bool = False
    ) -> None:
        """Push a tag to the remote.

        Parameters
        ----------
        version: str
            The tag name.
        commit: str | None
            The tagged commit; defaults to the first commit.
        annotated: bool
            Create an annotated tag instead of a lightweight one.

        """
        target = commit or self.commit
        if annotated:
            self.git("tag", "-a", version, target, "-m", "release fixture")
            self.git("push", "origin", f"refs/tags/{version}")
        else:
            self.git("push", "origin", f"{target}:refs/tags/{version}")

    def remote_tags(self) -> str:
        """Return the object SHAs of all tags on the remote.

        Returns
        -------
        str
            One SHA per line.

        """
        return self.git(
            "for-each-ref", "--format=%(objectname)", "refs/tags/", remote=True
        )


@pytest.fixture
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> ReleaseRepository:
    """Create a clone with one commit on ``main``, pushed to a bare remote.

    The working directory is the clone, as in a release workflow.

    Parameters
    ----------
    tmp_path: Path
        Temporary directory for the repositories.
    monkeypatch: pytest.MonkeyPatch
        Sets the Git environment and the working directory.

    Returns
    -------
    ReleaseRepository
        The repository fixture.

    """
    for name, value in {
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_AUTHOR_NAME": "Release fixture",
        "GIT_COMMITTER_NAME": "Release fixture",
        "GIT_AUTHOR_EMAIL": "fixture@example.invalid",
        "GIT_COMMITTER_EMAIL": "fixture@example.invalid",
    }.items():
        monkeypatch.setenv(name, value)

    result = ReleaseRepository(
        root=tmp_path, remote=tmp_path / "remote.git", branch=tmp_path / "branch"
    )
    for arguments in (
        ("init", "--bare", str(result.remote)),
        ("init", str(result.branch)),
    ):
        subprocess.run(  # noqa: S603 - no shell, test git commands
            ["git", *arguments], check=True, capture_output=True
        )
    result.git("remote", "add", "origin", str(result.remote))
    result.tree = result.git("mktree", stdin="")
    result.commit = result.new_commit("fixture")
    result.git("update-ref", "refs/heads/main", result.commit)
    result.git("symbolic-ref", "HEAD", "refs/heads/main")
    result.git("push", "origin", "main")
    monkeypatch.chdir(result.branch)
    return result


@dataclass
class FakeGitHub:
    """Answer release and workflow-run requests like the GitHub REST API."""

    repository: str = "MolarVerse/PQ"
    release: dict[str, Any] | None = None
    runs: dict[str, list] = field(default_factory=dict)
    requests: list[tuple[str, dict | None, dict | None]] = field(default_factory=list)
    posts: list[dict] = field(default_factory=list)
    get_error: Exception | None = None
    post_error: Exception | None = None
    get_body: Any = None

    def request(
        self,
        path: str,
        *,
        query: dict | None = None,
        data: dict | None = None,
        allow_missing: bool = False,
    ) -> Any:
        """Record a request and return the fake answer.

        Parameters
        ----------
        path: str
            The API path.
        query: dict | None
            Query parameters.
        data: dict | None
            The POST body.
        allow_missing: bool
            Return None when the release does not exist.

        Returns
        -------
        Any
            The fake response.

        Raises
        ------
        Exception
            The configured error for GET or POST requests.

        """
        self.requests.append((path, query, data))
        if "/actions/workflows/" in path:
            return {"workflow_runs": self.runs.get(path.split("/")[-2], [])}
        if data is not None:
            self.posts.append(data)
            self.release = {**data, "published_at": "2026-01-01T00:00:00Z"}
            if self.post_error:
                raise self.post_error
            return self.release
        if self.get_error:
            raise self.get_error
        if self.get_body is not None:
            return self.get_body
        if self.release is None and allow_missing:
            return None
        return self.release


@pytest.fixture
def github() -> FakeGitHub:
    """Return a fake GitHub client.

    Returns
    -------
    FakeGitHub
        The fake client.

    """
    return FakeGitHub()
