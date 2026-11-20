"""Tests for devops.git.remote."""

from __future__ import annotations

import typing

import pytest

from devops.config import GitConfig
from devops.git.remote import (
    GitRemoteError,
    git,
    ls_remote,
    remote_tag_target,
    remote_tags,
)

if typing.TYPE_CHECKING:
    from tests.conftest import ReleaseRepository


def test_git_errors_carry_the_command(repo: ReleaseRepository) -> None:  # noqa: ARG001
    """A failing Git command raises GitRemoteError with the command."""
    with pytest.raises(GitRemoteError, match="git rev-parse no-such-ref"):
        git("rev-parse", "no-such-ref")


def test_ls_remote_lists_matching_refs(repo: ReleaseRepository) -> None:
    """ls_remote maps reference names to SHAs."""
    assert ls_remote("refs/heads/main") == {"refs/heads/main": repo.commit}
    assert ls_remote("refs/tags/none") == {}


def test_remote_tags_skip_other_formats(repo: ReleaseRepository) -> None:
    """Only <prefix>X.Y.Z tags are returned."""
    for tag in ("v1.0.0", "v1.0.0-rc1", "1.1.0", "latest"):
        repo.tag(tag)
    assert [str(tag) for tag in remote_tags(GitConfig(tag_prefix="v"))] == ["v1.0.0"]


def test_remote_tag_target_peels_annotated_tags(repo: ReleaseRepository) -> None:
    """Annotated tags resolve to their commit; missing tags give None."""
    repo.tag("v1.0.0", annotated=True)
    assert remote_tag_target("v1.0.0") == repo.commit
    assert remote_tag_target("v2.0.0") is None
