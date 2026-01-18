"""Script for updating the changelog file."""

import sys

import typer

from devops.files import update_changelog
from devops.files.update_changelog import DevOpsChangelogError
from devops.utils import mstd_print

app = typer.Typer()


@app.command()
def main(version: str) -> None:
    """Update the changelog file with a new version entry.

    Parameters
    ----------
    version: str
        The new version to add to the changelog.

    """
    try:
        update_changelog.update_changelog(version)
        mstd_print(f"✅ CHANGELOG.md updated for version {version}")
    except DevOpsChangelogError as e:
        mstd_print(f"❌ Error updating changelog: {e}")
        sys.exit(1)


if __name__ == "__main__":
    app()
