"""Script with the release commands used by the release workflows."""

from __future__ import annotations

import re
import sys

import typer

from devops import __GLOBAL_CONFIG__
from devops.git.remote import GitRemoteError
from devops.release import (
    GitHubClient,
    ReleaseError,
    check_release_refs,
    extract_reviewers,
    publish_release,
    resolve_version,
    wait_for_ci,
)
from devops.release.version import check_version_format

app = typer.Typer(help="Release commands for the shared release workflows.")

REPOSITORY = re.compile(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+")
FULL_SHA = re.compile(r"[0-9a-f]{40}")


def _fail(error: Exception) -> typer.Exit:
    """Print an error to stderr and return the exit to raise.

    Parameters
    ----------
    error: Exception
        The error to report.

    Returns
    -------
    typer.Exit
        An exit with code 1.

    """
    typer.echo(getattr(error, "message", str(error)), err=True)
    return typer.Exit(code=1)


def _check_repository(repository: str) -> None:
    """Reject a repository that is not ``owner/name``.

    Parameters
    ----------
    repository: str
        The repository argument.

    Raises
    ------
    typer.BadParameter
        If the repository is not ``owner/name``.

    """
    if not REPOSITORY.fullmatch(repository):
        msg = "repository must use owner/name"
        raise typer.BadParameter(msg)


@app.command()
def version(
    head_ref: str = typer.Option(..., help="Source branch of the release PR."),
    title: str | None = typer.Option(None, help="Title of the release PR."),
    prepare: bool = typer.Option(
        False, help="Also check that the tag is new and a hotfix follows the latest."
    ),
) -> None:
    """Print the release tag for a release or hotfix branch."""
    try:
        typer.echo(
            resolve_version(
                head_ref, title, prepare=prepare, config=__GLOBAL_CONFIG__.git
            )
        )
    except (ReleaseError, GitRemoteError) as error:
        raise _fail(error) from error


@app.command("check-refs")
def check_refs(version: str) -> None:
    """Fail if the release tag or the release branch already exists."""
    try:
        check_release_refs(version, __GLOBAL_CONFIG__.git)
    except (ReleaseError, GitRemoteError) as error:
        raise _fail(error) from error
    typer.echo(f"Release tag and branch for {version} are available.")


@app.command()
def reviewers(repository: str) -> None:
    """Print the human PR authors of the release notes read from stdin."""
    _check_repository(repository)
    for login in extract_reviewers(sys.stdin.read(), repository):
        typer.echo(login)


@app.command("wait-ci")
def wait_ci(repository: str, sha: str) -> None:
    """Wait until the configured CI workflows succeeded on the release commit."""
    _check_repository(repository)
    if not FULL_SHA.fullmatch(sha):
        msg = "publication requires a full commit SHA"
        raise typer.BadParameter(msg)
    try:
        wait_for_ci(
            GitHubClient(),
            repository,
            sha,
            __GLOBAL_CONFIG__.release,
            echo=typer.echo,
        )
    except ReleaseError as error:
        raise _fail(error) from error


@app.command()
def publish(repository: str, version: str) -> None:
    """Tag HEAD and publish its GitHub release; safe to re-run."""
    _check_repository(repository)
    try:
        check_version_format(version, __GLOBAL_CONFIG__.git)
        target = publish_release(GitHubClient(), repository, version)
    except (ReleaseError, GitRemoteError) as error:
        raise _fail(error) from error
    typer.echo(f"Verified published release {version} at {target}.")
