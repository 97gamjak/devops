"""Tests for the devops_release CLI."""

from __future__ import annotations

import typing
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from devops.config import GitConfig, ReleaseConfig
from devops.release import ReleaseError
from devops.scripts.release import app

if typing.TYPE_CHECKING:
    from typing import Any

runner = CliRunner()
SHA = "a" * 40


@pytest.fixture(autouse=True)
def config() -> typing.Iterator[None]:
    """Use a v-prefixed tag config and one CI workflow."""
    with (
        patch("devops.scripts.release.__GLOBAL_CONFIG__") as global_config,
    ):
        global_config.git = GitConfig(tag_prefix="v")
        global_config.release = ReleaseConfig(ci_workflows=["ci.yml"])
        yield


def invoke(*arguments: str, stdin: str | None = None) -> Any:
    """Run the CLI and return the result."""
    return runner.invoke(app, list(arguments), input=stdin)


def test_help_lists_all_commands() -> None:
    """Every release command is registered."""
    result = invoke("--help")
    assert result.exit_code == 0
    for command in ("version", "check-refs", "reviewers", "wait-ci", "publish"):
        assert command in result.stdout


def test_version_prints_the_tag() -> None:
    """Version prints the resolved tag."""
    result = invoke(
        "version", "--head-ref", "release/v1.2.3", "--title", "Release-1.2.3"
    )
    assert result.exit_code == 0, result.output
    assert result.stdout.strip() == "v1.2.3"


def test_version_errors_exit_with_one() -> None:
    """A bad branch exits 1 with the message on stderr."""
    result = invoke("version", "--head-ref", "main")
    assert result.exit_code == 1
    assert "release branches must use" in result.stderr


def test_check_refs_reports_free_refs() -> None:
    """check-refs prints a confirmation when nothing exists."""
    with patch("devops.scripts.release.check_release_refs") as check:
        result = invoke("check-refs", "v1.0.0")
    assert result.exit_code == 0
    check.assert_called_once()
    assert "available" in result.stdout


def test_check_refs_errors_exit_with_one() -> None:
    """An existing tag exits 1."""
    with patch(
        "devops.scripts.release.check_release_refs",
        side_effect=ReleaseError("Release tag or branch for v1.0.0 already exists"),
    ):
        result = invoke("check-refs", "v1.0.0")
    assert result.exit_code == 1
    assert "already exists" in result.stderr


def test_reviewers_reads_stdin() -> None:
    """Reviewers prints one login per line."""
    notes = "* fix by @ape33 in https://github.com/o/r/pull/1\n"
    result = invoke("reviewers", "o/r", stdin=notes)
    assert result.exit_code == 0
    assert result.stdout == "ape33\n"


@pytest.mark.parametrize(
    "arguments",
    [
        ("reviewers", "not-a-repo"),
        ("wait-ci", "o/r", "abc"),
        ("publish", "bad", "v1.0.0"),
    ],
)
def test_bad_arguments_are_rejected(arguments: tuple[str, ...]) -> None:
    """Malformed repositories and SHAs are usage errors."""
    assert invoke(*arguments).exit_code == 2


def test_wait_ci_uses_the_release_config() -> None:
    """wait-ci passes the configured workflows."""
    with patch("devops.scripts.release.wait_for_ci") as wait:
        result = invoke("wait-ci", "o/r", SHA)
    assert result.exit_code == 0
    assert wait.call_args.args[1:] == (
        "o/r",
        SHA,
        ReleaseConfig(ci_workflows=["ci.yml"]),
    )
    wait.call_args.kwargs["echo"]("line")


def test_wait_ci_errors_exit_with_one() -> None:
    """A failed CI gate exits 1."""
    with patch(
        "devops.scripts.release.wait_for_ci", side_effect=ReleaseError("ci.yml failed")
    ):
        result = invoke("wait-ci", "o/r", SHA)
    assert result.exit_code == 1
    assert "ci.yml failed" in result.stderr


def test_publish_checks_the_version_format() -> None:
    """Publish refuses a version without the tag prefix."""
    with patch("devops.scripts.release.publish_release") as publish:
        result = invoke("publish", "o/r", "1.0.0")
    assert result.exit_code == 1
    assert "vX.Y.Z" in result.stderr
    publish.assert_not_called()


def test_publish_reports_the_commit() -> None:
    """Publish prints the verified release commit."""
    with patch("devops.scripts.release.publish_release", return_value=SHA):
        result = invoke("publish", "o/r", "v1.0.0")
    assert result.exit_code == 0
    assert f"v1.0.0 at {SHA}" in result.stdout
