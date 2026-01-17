"""Script for updating the changelog file."""

import sys

import typer

from devops.config import config
from devops.files import update_changelog
from devops.files.update_changelog import DevOpsChangelogError
from devops.utils import mstd_print

app = typer.Typer()


@app.command()
def main(version: str, changelog_path: str | None) -> None:
    """Update the changelog file with a new version entry.

    Parameters
    ----------
    version: str
        The new version to add to the changelog.
    changelog_path: str | None
        The path to the changelog file. If None, it defaults
        to the default_changelog_path from the configuration file.
    """
    if changelog_path is None:
        changelog_path = config.file.default_changelog_path

    try:
        update_changelog.update_changelog(version, changelog_path)
        mstd_print(f"✅ CHANGELOG.md updated for version {version}")
    except DevOpsChangelogError as e:
        mstd_print(f"❌ Error updating changelog: {e}")
        sys.exit(1)


if __name__ == "__main__":
    app()
