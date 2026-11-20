"""Wait until CI succeeded on the release commit before publishing."""

from __future__ import annotations

import time
import typing

from .errors import ReleaseError

if typing.TYPE_CHECKING:
    from collections.abc import Callable
    from typing import Any

    from devops.config import ReleaseConfig

    from .github import GitHubClient


def latest_run(
    client: GitHubClient, repository: str, workflow: str, sha: str, branch: str
) -> dict[str, Any] | None:
    """Return the newest push run of a workflow on exactly this commit.

    Parameters
    ----------
    client: GitHubClient
        The GitHub client.
    repository: str
        The repository as ``owner/name``.
    workflow: str
        The workflow file name, for example ``ci.yml``.
    sha: str
        The full commit SHA.
    branch: str
        The release branch.

    Returns
    -------
    dict[str, Any] | None
        The newest matching run, or None if there is none yet.

    Raises
    ------
    ReleaseError
        If GitHub returns data in an unexpected shape.

    """
    response = client.request(
        f"/repos/{repository}/actions/workflows/{workflow}/runs",
        query={"head_sha": sha, "branch": branch, "event": "push", "per_page": 100},
    )
    try:
        runs = [
            run
            for run in response["workflow_runs"]
            if run["head_sha"] == sha
            and run["head_branch"] == branch
            and run["event"] == "push"
        ]
        return max(runs, key=lambda run: run["id"], default=None)
    except (KeyError, TypeError) as error:
        msg = f"GitHub returned unexpected run data for {workflow}"
        raise ReleaseError(msg) from error


def wait_for_ci(  # noqa: PLR0913
    client: GitHubClient,
    repository: str,
    sha: str,
    config: ReleaseConfig,
    *,
    echo: Callable[[str], None] = print,
    sleep: Callable[[float], None] = time.sleep,
    clock: Callable[[], float] = time.monotonic,
) -> None:
    """Block until every configured workflow succeeded on the release commit.

    Only push runs on the release branch for this exact commit count, and
    the newest run of each workflow decides. Any other conclusion than
    ``success`` fails at once; a missing or running workflow fails when the
    timeout is reached.

    Parameters
    ----------
    client: GitHubClient
        The GitHub client.
    repository: str
        The repository as ``owner/name``.
    sha: str
        The full commit SHA.
    config: ReleaseConfig
        The release configuration with workflows, branch and timing.
    echo: Callable[[str], None]
        Prints progress messages.
    sleep: Callable[[float], None]
        Waits between polls.
    clock: Callable[[], float]
        Returns monotonic time in seconds.

    Raises
    ------
    ReleaseError
        If a workflow did not succeed or the timeout is reached.

    """
    if not config.ci_workflows:
        msg = "no CI workflows configured; set release.ci_workflows in devops.toml"
        raise ReleaseError(msg)
    deadline = clock() + config.ci_timeout
    while True:
        pending = []
        for workflow in config.ci_workflows:
            run = latest_run(client, repository, workflow, sha, config.branch)
            if run is None or run.get("status") != "completed":
                pending.append(workflow)
            elif run.get("conclusion") != "success":
                msg = (
                    f"{workflow} did not succeed for {sha}: "
                    f"{run.get('conclusion')} ({run.get('html_url', '')})"
                )
                raise ReleaseError(msg)
        if not pending:
            echo(f"CI succeeded on {config.branch} at {sha}.")
            return
        remaining = deadline - clock()
        if remaining <= 0:
            msg = f"No successful CI for {sha}; still waiting for {', '.join(pending)}"
            raise ReleaseError(msg)
        echo(f"Waiting for {sha}: {', '.join(pending)}")
        sleep(min(config.ci_interval, remaining))
