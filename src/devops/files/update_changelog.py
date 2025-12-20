"""Module for updating the changelog file."""

import re
from datetime import UTC, datetime
from pathlib import Path

from devops.files.files import DevOpsFileNotFoundError
from devops.github import get_github_repo

from .config import __DEFAULT_ENCODING__

__CHANGELOG_PATH__ = Path("CHANGELOG.md")
__CHANGELOG_INSERTION_MARKER__ = "<!-- insertion marker -->"


class MSTDChangelogError(Exception):
    """Base class for changelog related errors."""

    def __init__(self, message: str) -> None:
        """Initialize the exception with a message."""
        super().__init__(f"MSTDChangelogError: {message}")
        self.message = message


def update_changelog(version: str, changelog_path: Path = __CHANGELOG_PATH__) -> None:
    """Update the changelog file with a new version entry.

    Parameters
    ----------
    version: str
        The new version to add to the changelog.
    changelog_path: Path
        The path to the changelog file.

    Raises
    ------
    DevOpsFileNotFoundError
        If the changelog file does not exist.
    MSTDChangelogError
        If the "## Next Release" marker is not found in the changelog.

    """
    if not changelog_path.is_file():
        raise DevOpsFileNotFoundError(changelog_path)

    with changelog_path.open("r", encoding=__DEFAULT_ENCODING__) as f:
        content = f.readlines()

    repo = get_github_repo()
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
        raise MSTDChangelogError(msg)

    changelog_path.write_text("".join(updated) + "\n", encoding=__DEFAULT_ENCODING__)
