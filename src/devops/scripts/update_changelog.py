"""Script for updating the changelog file."""

import sys
from pathlib import Path

import typer

from devops import __GLOBAL_CONFIG__
from devops.config import config
from devops.files.update_changelog import DevOpsChangelogError
from devops.files.update_changelog import update_changelog as update_changelog_func
from devops.utils import mstd_print

update_changelog = typer.Typer()
update_changelogs = typer.Typer()

# Alias for tests and backwards compatibility
app = update_changelog


@update_changelog.command()
def _update_changelog(version: str, changelog_path: str | None = None) -> None:
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
        changelog_path = __GLOBAL_CONFIG__.file.default_changelog_path
    else:
        changelog_path = Path(changelog_path)
    try:
        update_changelog_func(version, changelog_path)
        mstd_print(f"✅ CHANGELOG.md updated for version {version}")
    except DevOpsChangelogError as e:
        mstd_print(f"❌ Error updating changelog: {e}")
        sys.exit(1)


@update_changelogs.command()
def _update_changelogs(version: str, changelog_paths: list[str] | None = None) -> None:
    """Update multiple changelog files with a new version entry.

    Parameters
    ----------
    version: str
        The new version to add to the changelogs.
    changelog_paths: list[str] | None
        The list of paths to the changelog files. If None, it defaults
        to the changelog_paths from the configuration file.
    """
    if changelog_paths is None:
        changelog_paths = __GLOBAL_CONFIG__.file.changelog_paths
    else:
        changelog_paths = [Path(p) for p in changelog_paths]

    failed_updates = []

    for changelog_path in changelog_paths:
        try:
            update_changelog_func(version, changelog_path)
            mstd_print(f"✅ {changelog_path} updated for version {version}")
        except DevOpsChangelogError as e:
            mstd_print(f"❌ Error updating {changelog_path}: {e}")
            failed_updates.append(changelog_path)

    if failed_updates:
        sys.exit(1)
