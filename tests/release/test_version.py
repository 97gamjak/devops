"""Tests for devops.release.version and devops.release.refs."""

from __future__ import annotations

import typing

import pytest

from devops.config import GitConfig
from devops.git.remote import GitRemoteError
from devops.release import ReleaseError, check_release_refs, resolve_version
from devops.release.version import check_version_format

if typing.TYPE_CHECKING:
    from tests.conftest import ReleaseRepository

V = GitConfig(tag_prefix="v")


@pytest.fixture
def tagged(repo: ReleaseRepository) -> ReleaseRepository:
    """Return the repository with tag v0.7.1."""
    repo.tag("v0.7.1")
    return repo


def test_hotfix_version_comes_from_title_and_survives_new_tags(
    tagged: ReleaseRepository,
) -> None:
    """A hotfix version is checked against the latest tag only when preparing."""
    title = "Hotfix-0.7.2: correct a thing"
    assert resolve_version("hotfix/fix", title, prepare=True, config=V) == "v0.7.2"
    tagged.tag("v0.8.0")
    assert resolve_version("hotfix/fix", title, prepare=False, config=V) == "v0.7.2"


@pytest.mark.parametrize(
    "title", [None, "fix: correct a thing", "Hotfix-0.7", "Hotfix-0.7.2x"]
)
@pytest.mark.parametrize("prepare", [False, True])
def test_hotfix_title_must_carry_a_version(
    tagged: ReleaseRepository,  # noqa: ARG001
    title: str | None,
    *,
    prepare: bool,
) -> None:
    """A hotfix PR title without Hotfix-X.Y.Z is rejected."""
    with pytest.raises(ReleaseError, match=r"Hotfix-X\.Y\.Z"):
        resolve_version("hotfix/fix", title, prepare=prepare, config=V)


@pytest.mark.parametrize("title", ["Hotfix-0.7.3", "Hotfix-0.8.0", "Hotfix-0.7.1"])
def test_hotfix_version_must_follow_the_latest_tag(
    tagged: ReleaseRepository,  # noqa: ARG001
    title: str,
) -> None:
    """A hotfix must be the latest tag plus one patch."""
    with pytest.raises(ReleaseError, match=r"must be v0\.7\.2"):
        resolve_version("hotfix/fix", title, prepare=True, config=V)


def test_existing_tag_moves_the_expected_hotfix(tagged: ReleaseRepository) -> None:
    """Once v0.7.2 exists, the next hotfix must be v0.7.3."""
    tagged.tag("v0.7.2")
    with pytest.raises(ReleaseError, match=r"must be v0\.7\.3"):
        resolve_version("hotfix/fix", "Hotfix-0.7.2", prepare=True, config=V)


def test_hotfix_without_any_tag_fails(repo: ReleaseRepository) -> None:  # noqa: ARG001
    """Without a release tag there is no hotfix base."""
    with pytest.raises(ReleaseError, match="latest release tag"):
        resolve_version("hotfix/fix", "Hotfix-0.0.1", prepare=True, config=V)


def test_regular_release_validates_title_and_tag(tagged: ReleaseRepository) -> None:  # noqa: ARG001
    """A release PR needs the matching title and a new tag."""
    with pytest.raises(ReleaseError, match=r"Release-1\.0\.0"):
        resolve_version("release/v1.0.0", "Wrong title", prepare=True, config=V)
    assert (
        resolve_version("release/v1.0.0", "Release-1.0.0", prepare=True, config=V)
        == "v1.0.0"
    )
    assert resolve_version("release/v1.0.0", None, prepare=False, config=V) == "v1.0.0"
    with pytest.raises(ReleaseError, match="already exists"):
        resolve_version("release/v0.7.1", None, prepare=True, config=V)


def test_tag_prefix_comes_from_the_config(repo: ReleaseRepository) -> None:
    """Repositories without a tag prefix use release/X.Y.Z and X.Y.Z tags."""
    repo.tag("1.0.0")
    config = GitConfig(tag_prefix="")
    assert (
        resolve_version("release/1.1.0", "Release-1.1.0", prepare=True, config=config)
        == "1.1.0"
    )
    assert (
        resolve_version("hotfix/x", "Hotfix-1.0.1", prepare=True, config=config)
        == "1.0.1"
    )
    with pytest.raises(ReleaseError, match=r"release/X\.Y\.Z"):
        resolve_version("release/v1.1.0", None, prepare=False, config=config)


@pytest.mark.parametrize("head_ref", ["main", "hotfix/", "release/1.0.0", "feature/x"])
def test_other_branches_are_not_releases(head_ref: str) -> None:
    """Only release/<tag> and hotfix/<name> branches make releases."""
    with pytest.raises(ReleaseError, match="release branches must use"):
        resolve_version(head_ref, None, prepare=False, config=V)


def test_tag_order_is_numeric_and_prerelease_tags_are_ignored(
    tagged: ReleaseRepository,
) -> None:
    """v0.10.0 is newer than v0.9.0, and v99.0.0-rc1 is not a release."""
    for tag in ("v0.9.0", "v0.10.0", "v99.0.0-rc1"):
        tagged.tag(tag, annotated=True)
    assert (
        resolve_version("hotfix/fix", "Hotfix-0.10.1", prepare=True, config=V)
        == "v0.10.1"
    )


def test_remote_failure_blocks_preparation(tagged: ReleaseRepository) -> None:
    """A Git error is raised, never read as "no tags"."""
    tagged.git("remote", "set-url", "origin", str(tagged.root / "missing.git"))
    with pytest.raises(GitRemoteError):
        resolve_version("hotfix/fix", "Hotfix-0.7.2", prepare=True, config=V)


def test_release_refs_are_free_until_tag_or_branch_exists(
    repo: ReleaseRepository,
) -> None:
    """check_release_refs fails for an existing tag or release branch."""
    check_release_refs("v1.0.0", V)
    repo.git("push", "origin", f"{repo.commit}:refs/heads/release/v1.0.0")
    with pytest.raises(ReleaseError, match="already exists"):
        check_release_refs("v1.0.0", V)
    repo.tag("v1.1.0")
    with pytest.raises(ReleaseError, match="already exists"):
        check_release_refs("v1.1.0", V)


def test_release_refs_fail_on_git_errors(repo: ReleaseRepository) -> None:
    """A missing remote is an error, not a free reference."""
    repo.git("remote", "set-url", "origin", str(repo.root / "missing.git"))
    with pytest.raises(GitRemoteError):
        check_release_refs("v1.0.0", V)


@pytest.mark.parametrize("version", ["1.0.0", "v1.0", "v1.0.0-rc1", "vv1.0.0"])
def test_version_format_uses_the_prefix(version: str) -> None:
    """Versions must be <prefix>X.Y.Z."""
    with pytest.raises(ReleaseError, match=r"vX\.Y\.Z"):
        check_version_format(version, V)
