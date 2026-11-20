"""Tests for devops.release.ci."""

from __future__ import annotations

import typing

import pytest

from devops.config import ReleaseConfig
from devops.release import ReleaseError, wait_for_ci

if typing.TYPE_CHECKING:
    from typing import Any

    from tests.conftest import FakeGitHub

SHA = "a" * 40
CONFIG = ReleaseConfig(ci_workflows=["lint.yml", "ci.yml"], ci_timeout=0)


def run(**changes: Any) -> dict[str, Any]:
    """Return a successful push run on main for SHA, with changes applied."""
    return {
        "id": 10,
        "head_sha": SHA,
        "head_branch": "main",
        "event": "push",
        "status": "completed",
        "conclusion": "success",
        **changes,
    }


class Clock:
    """A fake monotonic clock that advances when sleeping."""

    def __init__(self) -> None:
        """Start at zero."""
        self.now = 0.0
        self.sleeps: list[float] = []

    def __call__(self) -> float:
        """Return the current time."""
        return self.now

    def sleep(self, seconds: float) -> None:
        """Advance the time."""
        self.sleeps.append(seconds)
        self.now += seconds


def wait(github: FakeGitHub, config: ReleaseConfig = CONFIG) -> list[str]:
    """Run the CI gate with a fake clock and return the printed lines."""
    clock = Clock()
    lines: list[str] = []
    wait_for_ci(
        github,
        "MolarVerse/PQ",
        SHA,
        config,
        echo=lines.append,
        sleep=clock.sleep,
        clock=clock,
    )
    return lines


def test_requires_every_workflow_for_the_exact_commit(github: FakeGitHub) -> None:
    """All configured workflows are queried for push runs on the release branch."""
    github.runs = {"lint.yml": [run()], "ci.yml": [run()]}
    assert wait(github) == [f"CI succeeded on main at {SHA}."]
    assert [path for path, _, _ in github.requests] == [
        "/repos/MolarVerse/PQ/actions/workflows/lint.yml/runs",
        "/repos/MolarVerse/PQ/actions/workflows/ci.yml/runs",
    ]
    assert github.requests[0][1] == {
        "head_sha": SHA,
        "branch": "main",
        "event": "push",
        "per_page": 100,
    }


@pytest.mark.parametrize(
    "conclusion",
    ["failure", "cancelled", "timed_out", "skipped", "neutral", "action_required"],
)
def test_any_other_conclusion_blocks_publication(
    github: FakeGitHub, conclusion: str
) -> None:
    """Only success passes the gate."""
    github.runs = {"lint.yml": [run()], "ci.yml": [run(conclusion=conclusion)]}
    with pytest.raises(ReleaseError, match=conclusion):
        wait(github)


@pytest.mark.parametrize(
    "changes",
    [{"head_sha": "b" * 40}, {"head_branch": "dev"}, {"event": "pull_request"}],
)
def test_other_commits_branches_and_events_do_not_count(
    github: FakeGitHub, changes: dict[str, str]
) -> None:
    """Runs of other commits, branches or PR checks cannot satisfy the gate."""
    github.runs = {"lint.yml": [run()], "ci.yml": [run(**changes)]}
    with pytest.raises(ReleaseError, match=r"still waiting for ci\.yml"):
        wait(github)


def test_newest_run_decides(github: FakeGitHub) -> None:
    """A newer failure or pending run beats an older success, and vice versa."""
    github.runs = {
        "lint.yml": [run()],
        "ci.yml": [run(id=11, conclusion="failure"), run()],
    }
    with pytest.raises(ReleaseError, match="failure"):
        wait(github)
    github.runs["ci.yml"] = [run(id=11, status="queued", conclusion=None), run()]
    with pytest.raises(ReleaseError, match="still waiting"):
        wait(github)
    github.runs["ci.yml"] = [run(id=9, conclusion="failure"), run()]
    wait(github)


def test_waits_until_ci_finishes(github: FakeGitHub) -> None:
    """Missing and running workflows are polled until they succeed."""
    answers = [[], [run(status="in_progress", conclusion=None)], [run()]]

    class Polling(type(github)):
        def request(self, path: str, **kwargs: Any) -> Any:
            if path.endswith("/ci.yml/runs"):
                self.runs["ci.yml"] = answers.pop(0) if len(answers) > 1 else answers[0]
            return super().request(path, **kwargs)

    polling = Polling(runs={"lint.yml": [run()]})
    lines = wait(
        polling, ReleaseConfig(ci_workflows=["lint.yml", "ci.yml"], ci_timeout=60)
    )
    assert lines[-1] == f"CI succeeded on main at {SHA}."
    assert lines.count(f"Waiting for {SHA}: ci.yml") == 2


def test_timeout_and_interval_come_from_the_config(github: FakeGitHub) -> None:
    """The gate sleeps ci_interval seconds and stops after ci_timeout."""
    clock = Clock()
    config = ReleaseConfig(ci_workflows=["ci.yml"], ci_timeout=50, ci_interval=20)
    with pytest.raises(ReleaseError, match="still waiting"):
        wait_for_ci(
            github,
            "o/r",
            SHA,
            config,
            echo=lambda _: None,
            sleep=clock.sleep,
            clock=clock,
        )
    assert clock.sleeps == [20, 20, 10]


def test_branch_comes_from_the_config(github: FakeGitHub) -> None:
    """A repository can release from another branch."""
    github.runs = {"ci.yml": [run(head_branch="master")]}
    wait(github, ReleaseConfig(branch="master", ci_workflows=["ci.yml"]))
    assert github.requests[0][1]["branch"] == "master"


def test_no_configured_workflow_is_an_error(github: FakeGitHub) -> None:
    """Publishing without a CI gate must be a deliberate config choice."""
    with pytest.raises(ReleaseError, match=r"release\.ci_workflows"):
        wait(github, ReleaseConfig())


@pytest.mark.parametrize("body", [None, [], {}, {"workflow_runs": [{}]}])
def test_malformed_api_data_blocks_publication(github: FakeGitHub, body: Any) -> None:
    """Unexpected run data is an error."""

    class Broken(type(github)):
        def request(self, path: str, **kwargs: Any) -> Any:  # noqa: ARG002
            return body

    with pytest.raises(ReleaseError, match="unexpected run data"):
        wait(Broken())
