"""Script for updating the changelog file."""

from __future__ import annotations

import sys
import typing
from dataclasses import replace

import typer

from devops import __GLOBAL_CONFIG__
from devops.git import GitTagError, get_latest_tag
from devops.utils import mstd_print

if typing.TYPE_CHECKING:
    from devops.git import GitTag

latest_tag = typer.Typer()
increase_tag = typer.Typer()


def _get_latest_tag(
    prefix: str | None = None, *, empty_tag_list_allowed: bool | None = None
) -> GitTag:
    """Retrieve the latest git tag.

    Parameters
    ----------
    prefix: str | None
        The expected prefix of the Git tags. If None, uses the default prefix.
    empty_tag_list_allowed: bool | None
        Whether to allow an empty tag list without raising an error. If None,
        uses the default setting.

    Returns
    -------
    GitTag
        The latest Git tag.

    """
    config = __GLOBAL_CONFIG__.git

    if prefix is None:
        prefix = config.tag_prefix
    if empty_tag_list_allowed is None:
        empty_tag_list_allowed = config.empty_tag_list_allowed

    config = replace(
        config,
        tag_prefix=prefix,
        empty_tag_list_allowed=empty_tag_list_allowed,
    )

    return get_latest_tag(config=config)


@latest_tag.command()
def get_latest_tag_script(
    prefix: str | None = None, *, empty_tag_list_allowed: bool | None = None
) -> None:
    """Retrieve and print the latest git tag.

    Parameters
    ----------
    prefix: str | None
        The expected prefix of the Git tags. If None, uses the default prefix.
    empty_tag_list_allowed: bool | None
        Whether to allow an empty tag list without raising an error. If None,
        uses the default setting.

    """
    try:
        latest_tag = _get_latest_tag(
            prefix=prefix,
            empty_tag_list_allowed=empty_tag_list_allowed,
        )
        mstd_print(str(latest_tag))
    except GitTagError as e:
        mstd_print(f"❌ Error retrieving latest git tag: {e}")
        sys.exit(1)


@increase_tag.command()
def increase_latest_tag(
    prefix: str | None = None,
    *,
    empty_tag_list_allowed: bool | None = None,
    major: bool = False,
    minor: bool = False,
    patch: bool = False,
) -> None:
    """Increase the latest git tag by major, minor, or patch.

    Parameters
    ----------
    major: bool
        Whether to increase the major version.
    minor: bool
        Whether to increase the minor version.
    patch: bool
        Whether to increase the patch version.

    """
    if sum([major, minor, patch]) != 1:
        mstd_print("❌ Please specify exactly one of --major, --minor, or --patch.")
        sys.exit(1)

    try:
        latest_tag = _get_latest_tag(
            prefix=prefix,
            empty_tag_list_allowed=empty_tag_list_allowed,
        )
    except GitTagError as e:
        mstd_print(f"❌ Error retrieving latest git tag: {e}")
        sys.exit(1)

    if major:
        new_tag = latest_tag.increase_major()
    elif minor:
        new_tag = latest_tag.increase_minor()
    else:  # patch
        new_tag = latest_tag.increase_patch()

    mstd_print(str(new_tag))
