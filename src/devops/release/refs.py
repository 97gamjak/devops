"""Check that a release tag and its release branch are still free."""

from __future__ import annotations

import typing

from devops.git.remote import ls_remote

from .errors import ReleaseError
from .version import check_version_format

if typing.TYPE_CHECKING:
    from devops.config import GitConfig


def check_release_refs(version: str, config: GitConfig) -> None:
    """Fail if the tag or the ``release/<version>`` branch already exists.

    Git errors are raised, never read as "the reference is missing".

    Parameters
    ----------
    version: str
        The release tag, for example ``v1.2.3``.
    config: GitConfig
        The Git configuration with the tag prefix.

    Raises
    ------
    ReleaseError
        If the version is malformed or the tag or branch exists.

    """
    check_version_format(version, config)
    if ls_remote(f"refs/tags/{version}", f"refs/heads/release/{version}"):
        msg = f"Release tag or branch for {version} already exists"
        raise ReleaseError(msg)
