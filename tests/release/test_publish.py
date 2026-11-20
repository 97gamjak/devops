"""Tests for devops.release.publish."""

from __future__ import annotations

import typing

import pytest

from devops.git.remote import GitRemoteError
from devops.release import ReleaseError, publish_release

if typing.TYPE_CHECKING:
    from typing import Any

    from tests.conftest import FakeGitHub, ReleaseRepository

VERSION = "v9.9.9"
REPOSITORY = "MolarVerse/PQ"


def published(**changes: Any) -> dict[str, Any]:
    """Return a published stable release of VERSION, with changes applied."""
    return {
        "tag_name": VERSION,
        "draft": False,
        "prerelease": False,
        "published_at": "2026-01-01T00:00:00Z",
        **changes,
    }


def test_creates_tag_and_release_then_retries_without_a_second_post(
    repo: ReleaseRepository, github: FakeGitHub
) -> None:
    """A first run tags HEAD and creates the release; a re-run only verifies."""
    assert publish_release(github, REPOSITORY, VERSION) == repo.commit
    assert repo.remote_tags() == repo.commit
    assert github.posts == [
        {
            "tag_name": VERSION,
            "target_commitish": repo.commit,
            "name": VERSION,
            "draft": False,
            "prerelease": False,
            "generate_release_notes": True,
        }
    ]
    assert publish_release(github, REPOSITORY, VERSION) == repo.commit
    assert len(github.posts) == 1


def test_existing_annotated_tag_is_kept(
    repo: ReleaseRepository, github: FakeGitHub
) -> None:
    """An annotated tag on HEAD is accepted and not replaced."""
    repo.tag(VERSION, annotated=True)
    original = repo.remote_tags()
    assert original != repo.commit
    github.release = published()
    publish_release(github, REPOSITORY, VERSION)
    assert repo.remote_tags() == original
    assert github.posts == []


def test_tag_on_another_commit_is_never_replaced(
    repo: ReleaseRepository, github: FakeGitHub
) -> None:
    """Local or remote tags on another commit stop the run."""
    other = repo.new_commit("other", parent=repo.commit)
    repo.git("tag", VERSION, other)
    with pytest.raises(ReleaseError, match="local tag"):
        publish_release(github, REPOSITORY, VERSION)
    assert repo.remote_tags() == ""

    repo.tag(VERSION, commit=other)
    github.requests.clear()
    with pytest.raises(ReleaseError, match="another commit"):
        publish_release(github, REPOSITORY, VERSION)
    assert repo.remote_tags() == other
    assert github.requests == []
    assert github.posts == []


@pytest.mark.parametrize(
    "changes",
    [
        {"draft": True},
        {"prerelease": True},
        {"published_at": None},
        {"tag_name": "v0.0.0"},
    ],
)
def test_unpublished_or_wrong_releases_are_not_reported_as_published(
    repo: ReleaseRepository, github: FakeGitHub, changes: dict[str, Any]
) -> None:
    """Drafts, pre-releases and incomplete records stop the run."""
    repo.tag(VERSION)
    github.release = published(**changes)
    with pytest.raises(ReleaseError, match="not a published stable release"):
        publish_release(github, REPOSITORY, VERSION)
    assert github.posts == []


def test_release_without_its_tag_needs_manual_recovery(
    repo: ReleaseRepository, github: FakeGitHub
) -> None:
    """A release whose tag is gone is not re-tagged automatically."""
    github.release = published()
    with pytest.raises(ReleaseError, match="has no tag"):
        publish_release(github, REPOSITORY, VERSION)
    assert repo.remote_tags() == ""


@pytest.mark.parametrize("body", [[], "text", 3])
def test_invalid_release_data_creates_nothing(
    repo: ReleaseRepository, github: FakeGitHub, body: Any
) -> None:
    """A non-object answer from GitHub stops before tagging."""
    github.get_body = body
    with pytest.raises(ReleaseError, match="invalid release data"):
        publish_release(github, REPOSITORY, VERSION)
    assert repo.remote_tags() == ""
    assert github.posts == []


def test_api_outage_creates_nothing(
    repo: ReleaseRepository, github: FakeGitHub
) -> None:
    """A failing release lookup stops before tagging."""
    github.get_error = ReleaseError("GitHub returned HTTP 500")
    with pytest.raises(ReleaseError, match="HTTP 500"):
        publish_release(github, REPOSITORY, VERSION)
    assert repo.remote_tags() == ""


def test_post_failure_after_write_is_finished_by_a_retry(
    repo: ReleaseRepository, github: FakeGitHub
) -> None:
    """If GitHub created the release but the answer was lost, a re-run verifies it."""
    github.post_error = ReleaseError("GitHub returned HTTP 503")
    with pytest.raises(ReleaseError, match="HTTP 503"):
        publish_release(github, REPOSITORY, VERSION)
    github.post_error = None
    assert publish_release(github, REPOSITORY, VERSION) == repo.commit
    assert len(github.posts) == 1


def test_push_failure_is_reported(repo: ReleaseRepository, github: FakeGitHub) -> None:
    """A remote that rejects the tag push stops the run."""
    repo.git("config", "remote.origin.pushurl", str(repo.root / "missing.git"))
    with pytest.raises(GitRemoteError, match="push"):
        publish_release(github, REPOSITORY, VERSION)
    assert github.posts == []


def test_tag_moved_during_publication_is_detected(
    repo: ReleaseRepository, github: FakeGitHub, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A tag that moves while the release is created fails the final check."""
    other = repo.new_commit("other", parent=repo.commit)
    original = type(github).request

    def move_tag(self: FakeGitHub, path: str, **kwargs: Any) -> Any:
        answer = original(self, path, **kwargs)
        if kwargs.get("data") is not None:
            repo.git("push", "--force", "origin", f"{other}:refs/tags/{VERSION}")
        return answer

    monkeypatch.setattr(type(github), "request", move_tag)
    with pytest.raises(ReleaseError, match="moved away"):
        publish_release(github, REPOSITORY, VERSION)
