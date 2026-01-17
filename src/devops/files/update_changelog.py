"""Module for updating the changelog file."""

import re
from datetime import UTC, datetime
from pathlib import Path

from devops.config import Constants
from devops.files import open_file, write_text

__CHANGELOG_PATH__ = Path("CHANGELOG.md")
__CHANGELOG_INSERTION_MARKER__ = "<!-- insertion marker -->"


class DevOpsChangelogError(Exception):
    """Base class for changelog related errors."""

    def __init__(self, message: str) -> None:
        """Initialize the exception with a message."""
        super().__init__(f"DevOpsChangelogError: {message}")
        self.message = message


def update_changelog(version: str, changelog_path: Path) -> None:
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
        If the changelog file does not exist. Happens inside open_file.
    DevOpsChangelogError
        If the "## Next Release" marker is not found in the changelog.

    """
    with open_file(changelog_path, mode="r") as f:
        content = f.readlines()

    repo = Constants.github.github_default_owner_url
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
