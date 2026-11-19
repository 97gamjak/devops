"""Module for querying and pushing references on the ``origin`` remote."""

from __future__ import annotations

import subprocess
import typing

from devops.git.tag import GitTag, GitTagError

if typing.TYPE_CHECKING:
    from devops.config import GitConfig


class GitRemoteError(Exception):
    """Exception raised when a Git command fails."""

    def __init__(self, message: str) -> None:
        """Initialize the exception with a message."""
        super().__init__(f"GitRemoteError: {message}")
        self.message = message


def git(*arguments: str) -> str:
    """Run a Git command and return its stripped standard output.

    Parameters
    ----------
    *arguments: str
        The arguments passed to ``git``.

    Returns
    -------
    str
        The stripped standard output of the command.

    Raises
    ------
    GitRemoteError
        If Git cannot be run or exits with an error.

    """
    try:
        result = subprocess.run(  # noqa: S603 - no shell, args are git subcommands
            ["git", *arguments],
            capture_output=True,
            text=True,
            check=True,
        )
    except (OSError, subprocess.CalledProcessError) as error:
        stderr = getattr(error, "stderr", "") or ""
        msg = f"'git {' '.join(arguments)}' failed: {stderr.strip() or error}"
        raise GitRemoteError(msg) from error
    return result.stdout.strip()


def ls_remote(*patterns: str, options: tuple[str, ...] = ()) -> dict[str, str]:
    """List references on ``origin`` that match the given patterns.

    Parameters
    ----------
    *patterns: str
        Reference patterns, for example ``refs/tags/v1.0.0``.
    options: tuple[str, ...]
        Options for ``git ls-remote``, for example ``("--tags",)``.

    Returns
    -------
    dict[str, str]
        A mapping of reference name to commit or tag object SHA.

    """
    references = {}
    for line in git("ls-remote", *options, "origin", *patterns).splitlines():
        sha, reference = line.split()
        references[reference] = sha
    return references


def remote_tags(config: GitConfig) -> list[GitTag]:
    """Return all release tags on ``origin`` that match the configured prefix.

    Tags that are not ``<prefix>major.minor.patch``, such as pre-releases,
    are ignored.

    Parameters
    ----------
    config: GitConfig
        The Git configuration with the expected tag prefix.

    Returns
    -------
    list[GitTag]
        The release tags found on ``origin``.

    """
    tags = []
    for reference in ls_remote(options=("--tags", "--refs")):
        try:
            tags.append(
                GitTag.from_string(reference.removeprefix("refs/tags/"), config)
            )
        except GitTagError:
            continue
    return tags


def remote_tag_target(tag: str) -> str | None:
    """Return the commit a tag on ``origin`` points to.

    Parameters
    ----------
    tag: str
        The tag name.

    Returns
    -------
    str | None
        The commit SHA, or None if the tag does not exist on ``origin``.

    """
    references = ls_remote(f"refs/tags/{tag}", f"refs/tags/{tag}^{{}}")
    return references.get(f"refs/tags/{tag}^{{}}", references.get(f"refs/tags/{tag}"))
