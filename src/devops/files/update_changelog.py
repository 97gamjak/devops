"""Module for updating the changelog file."""

import os
import re
import subprocess
from datetime import UTC, datetime
from pathlib import Path

from devops.config import Constants
from devops.files import open_file, write_text

__CHANGELOG_PATH__ = Path("CHANGELOG.md")
__CHANGELOG_INSERTION_MARKER__ = "<!-- insertion marker -->"
__GITHUB_REMOTE_PATTERN__ = re.compile(r"github\.com[:/]([^/]+/[^/]+?)(?:\.git)?/?$")


class DevOpsChangelogError(Exception):
    """Base class for changelog related errors."""

    def __init__(self, message: str) -> None:
        """Initialize the exception with a message."""
        super().__init__(f"DevOpsChangelogError: {message}")
        self.message = message


def get_repo_url() -> str:
    """Return the GitHub URL of the current repository.

    Uses ``GITHUB_REPOSITORY`` (and ``GITHUB_SERVER_URL``) when set, as in
    GitHub Actions, and the ``origin`` remote otherwise.

    Returns
    -------
    str
        The repository URL, for example ``https://github.com/MolarVerse/devops``.

    Raises
    ------
    DevOpsChangelogError
        If the repository cannot be determined.

    """
    repository = os.environ.get("GITHUB_REPOSITORY")
    if repository:
        server = os.environ.get("GITHUB_SERVER_URL") or Constants.github.github_url
        return f"{server.rstrip('/')}/{repository}"

    try:
        remote = subprocess.check_output(
            ["git", "remote", "get-url", "origin"],
            stderr=subprocess.DEVNULL,
            text=True,
            shell=False,
        ).strip()
    except (OSError, subprocess.CalledProcessError) as e:
        msg = "Cannot find the GitHub repository; set GITHUB_REPOSITORY=owner/repo"
        raise DevOpsChangelogError(msg) from e

    match = __GITHUB_REMOTE_PATTERN__.search(remote)
    if match is None:
        msg = f"origin is not a GitHub remote: {remote}"
        raise DevOpsChangelogError(msg)

    return f"{Constants.github.github_url}/{match.group(1)}"


def update_changelog(
    version: str, changelog_path: Path, repo_url: str | None = None
) -> None:
    """Update the changelog file with a new version entry.

    Parameters
    ----------
    version: str
        The new version to add to the changelog.
    changelog_path: Path
        The path to the changelog file.
    repo_url: str | None
        The GitHub URL used for the release link. Defaults to
        :func:`get_repo_url`.

    Raises
    ------
    DevOpsFileNotFoundError
        If the changelog file does not exist. Happens inside open_file.
    DevOpsChangelogError
        If the "## Next Release" marker is not found in the changelog or the
        repository URL cannot be determined.

    """
    with open_file(changelog_path, mode="r") as f:
        content = f.readlines()

    repo = repo_url if repo_url is not None else get_repo_url()
    today = datetime.now(tz=UTC).date().isoformat()
    new_entry = f"## [{version}]({repo}/releases/tag/{version}) - {today}"

    updated = []
    marker_moved = False

    for line in content:
        # Find the "## Next Release" heading
        if not marker_moved and re.match(r"^##\s+Next Release", line):
            # Ensure marker comes right after "Next Release"
            # For formatting consistency, add newline characters to all appended lines
            updated.append(line + "\n")
            updated.append(__CHANGELOG_INSERTION_MARKER__ + "\n")
            updated.append(new_entry + "\n")
            marker_moved = True

        # Skip the old insertion marker wherever it was
        elif __CHANGELOG_INSERTION_MARKER__ in line:
            continue

        else:
            updated.append(line)

    if not marker_moved:
        msg = "Could not find '## Next Release' in CHANGELOG.md"
        raise DevOpsChangelogError(msg)

    write_text(changelog_path, "".join(updated) + "\n")
