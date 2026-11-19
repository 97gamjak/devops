"""Resolve the release version from the release branch or hotfix PR title."""

from __future__ import annotations

import re
import typing

from devops.git.remote import ls_remote, remote_tags
from devops.git.tag import GitTag

from .errors import ReleaseError

if typing.TYPE_CHECKING:
    from devops.config import GitConfig

VERSION = r"[0-9]+\.[0-9]+\.[0-9]+"
HOTFIX_TITLE = re.compile(rf"Hotfix-({VERSION})(?=$|[\s:])")


def check_version_format(version: str, config: GitConfig) -> None:
    """Fail unless the version is ``<prefix>X.Y.Z``.

    Parameters
    ----------
    version: str
        The release tag, for example ``v1.2.3``.
    config: GitConfig
        The Git configuration with the tag prefix.

    Raises
    ------
    ReleaseError
        If the version does not use the configured format.

    """
    if not re.fullmatch(rf"{re.escape(config.tag_prefix)}{VERSION}", version):
        msg = f"version must use {config.tag_prefix}X.Y.Z, not {version}"
        raise ReleaseError(msg)


def resolve_version(
    head_ref: str, title: str | None, *, prepare: bool, config: GitConfig
) -> str:
    """Return the release tag for a release or hotfix pull request.

    A release branch is ``release/<prefix>X.Y.Z`` and its PR title must be
    ``Release-X.Y.Z``. A hotfix branch is ``hotfix/<name>`` and its PR title
    must start with ``Hotfix-X.Y.Z``.

    Parameters
    ----------
    head_ref: str
        The source branch of the pull request.
    title: str | None
        The pull request title. None skips the release title check.
    prepare: bool
        Also check that the tag is new and that a hotfix follows the latest
        tag. Use it before the release; leave it off after the merge.
    config: GitConfig
        The Git configuration with the tag prefix.

    Returns
    -------
    str
        The release tag, for example ``v1.2.3``.

    Raises
    ------
    ReleaseError
        If the branch, title or version is not valid for a release.

    """
    prefix = config.tag_prefix
    release = re.fullmatch(rf"release/{re.escape(prefix)}({VERSION})", head_ref)
    if release:
        number = release.group(1)
        if title is not None and title != f"Release-{number}":
            msg = f"Release PR title must be Release-{number}."
            raise ReleaseError(msg)
    elif head_ref.startswith("hotfix/") and head_ref != "hotfix/":
        hotfix = HOTFIX_TITLE.match(title or "")
        if not hotfix:
            msg = (
                "Hotfix PR title must start with Hotfix-X.Y.Z, "
                "e.g. 'Hotfix-1.0.1: describe the fix'."
            )
            raise ReleaseError(msg)
        number = hotfix.group(1)
        if prepare:
            tags = remote_tags(config)
            if not tags:
                msg = "could not infer the latest release tag"
                raise ReleaseError(msg)
            expected = max(tags).increase_patch()
            if GitTag.from_string(prefix + number, config) != expected:
                msg = (
                    f"Hotfix version must be {expected} (latest tag + 1), "
                    f"not {prefix}{number}."
                )
                raise ReleaseError(msg)
    else:
        msg = (
            f"release branches must use release/{prefix}X.Y.Z or hotfix/<name>, "
            f"not {head_ref}"
        )
        raise ReleaseError(msg)

    version = prefix + number
    if prepare and ls_remote(f"refs/tags/{version}"):
        msg = f"{version} already exists; choose a new release version"
        raise ReleaseError(msg)
    return version
