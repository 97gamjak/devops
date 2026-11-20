"""Tag the release commit and publish its GitHub release, safe to re-run."""

from __future__ import annotations

import subprocess
import typing

from devops.git.remote import git, remote_tag_target

from .errors import ReleaseError

if typing.TYPE_CHECKING:
    from typing import Any

    from .github import GitHubClient


def get_release(
    client: GitHubClient, repository: str, version: str
) -> dict[str, Any] | None:
    """Return the GitHub release of a tag, or None if it does not exist.

    Parameters
    ----------
    client: GitHubClient
        The GitHub client.
    repository: str
        The repository as ``owner/name``.
    version: str
        The release tag.

    Returns
    -------
    dict[str, Any] | None
        The release, or None if GitHub has no release for the tag.

    Raises
    ------
    ReleaseError
        If GitHub returns something other than a release object.

    """
    release = client.request(
        f"/repos/{repository}/releases/tags/{version}", allow_missing=True
    )
    if release is not None and not isinstance(release, dict):
        msg = "GitHub returned invalid release data"
        raise ReleaseError(msg)
    return release


def verify_release(release: Any, version: str) -> None:
    """Fail unless the release is a published, stable release of the tag.

    Parameters
    ----------
    release: Any
        The release returned by GitHub.
    version: str
        The release tag.

    Raises
    ------
    ReleaseError
        If the release is a draft, a pre-release, unpublished or another tag.

    """
    if (
        not isinstance(release, dict)
        or release.get("tag_name") != version
        or release.get("draft") is not False
        or release.get("prerelease") is not False
        or not release.get("published_at")
    ):
        msg = f"{version} is not a published stable release; inspect it before retrying"
        raise ReleaseError(msg)


def push_tag(version: str, target: str) -> None:
    """Create the tag on the release commit if needed and push it.

    Parameters
    ----------
    version: str
        The release tag.
    target: str
        The release commit SHA.

    Raises
    ------
    ReleaseError
        If a local tag with this name points to another commit.

    """
    local = subprocess.run(  # noqa: S603 - no shell, args are git subcommands
        ["git", "show-ref", "--verify", "--quiet", f"refs/tags/{version}"],
        check=False,
    )
    if local.returncode == 1:
        git("tag", version, target)
    elif local.returncode != 0:
        msg = f"cannot read local tag {version}"
        raise ReleaseError(msg)
    elif git("rev-parse", f"refs/tags/{version}^{{commit}}") != target:
        msg = f"local tag {version} points to another commit"
        raise ReleaseError(msg)
    git("push", "origin", f"refs/tags/{version}")


def publish_release(client: GitHubClient, repository: str, version: str) -> str:
    """Tag ``HEAD`` and publish a stable GitHub release with generated notes.

    A re-run after a partial failure finishes the missing steps. An existing
    tag on another commit, or a release that is not published and stable,
    stops the run instead of being replaced.

    Parameters
    ----------
    client: GitHubClient
        The GitHub client.
    repository: str
        The repository as ``owner/name``.
    version: str
        The release tag.

    Returns
    -------
    str
        The release commit SHA.

    Raises
    ------
    ReleaseError
        If the tag or release cannot be created or verified.

    """
    target = git("rev-parse", "HEAD")
    existing_target = remote_tag_target(version)
    if existing_target is not None and existing_target != target:
        msg = f"{version} already points to another commit"
        raise ReleaseError(msg)

    release = get_release(client, repository, version)
    if release is not None:
        verify_release(release, version)
        if existing_target is None:
            msg = (
                f"existing release {version} has no tag; "
                "restore its original tag before retrying"
            )
            raise ReleaseError(msg)

    if existing_target is None:
        push_tag(version, target)
    if remote_tag_target(version) != target:
        msg = f"could not verify {version} on the release commit"
        raise ReleaseError(msg)

    if release is None:
        created = client.request(
            f"/repos/{repository}/releases",
            data={
                "tag_name": version,
                "target_commitish": target,
                "name": version,
                "draft": False,
                "prerelease": False,
                "generate_release_notes": True,
            },
        )
        verify_release(created, version)
        verify_release(get_release(client, repository, version), version)

    if remote_tag_target(version) != target:
        msg = f"{version} moved away from the release commit during publication"
        raise ReleaseError(msg)
    return target
