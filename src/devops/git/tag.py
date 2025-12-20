"""Module for Git tag-related constants and functions."""

from __future__ import annotations

import subprocess
import typing
from dataclasses import dataclass

from devops import __GLOBAL_CONFIG__

if typing.TYPE_CHECKING:
    from devops.config import GitConfig


# TODO(97gamjak): centralize exception handling
# https://github.com/97gamjak/devops/issues/24
class GitTagError(Exception):
    """Exception raised for Git tag-related errors in devops checks."""

    def __init__(self, message: str) -> None:
        """Initialize the exception with a message."""
        super().__init__(f"GitTagError: {message}")
        self.message = message


@dataclass(frozen=True, order=True)
class GitTag:
    """Class representing a Git tag."""

    major: int
    minor: int
    patch: int
    prefix: str

    def __str__(self) -> str:
        """Return the string representation of the Git tag.

        Returns
        -------
        str
            The string representation of the Git tag
            in the format 'v<major>.<minor>.<patch>'.

        """
        return f"{self.prefix}{self.major}.{self.minor}.{self.patch}"

    def increase_major(self) -> GitTag:
        """Increase the major version by 1 and reset minor and patch to 0.

        Returns
        -------
        GitTag
            A new GitTag instance with the increased major version.

        """
        return GitTag(self.major + 1, 0, 0, self.prefix)

    def increase_minor(self) -> GitTag:
        """Increase the minor version by 1 and reset patch to 0.

        Returns
        -------
        GitTag
            A new GitTag instance with the increased minor version.

        """
        return GitTag(self.major, self.minor + 1, 0, self.prefix)

    def increase_patch(self) -> GitTag:
        """Increase the patch version by 1.

        Returns
        -------
        GitTag
            A new GitTag instance with the increased patch version.

        """
        return GitTag(self.major, self.minor, self.patch + 1, self.prefix)

    @staticmethod
    def from_string(tag: str, config: GitConfig = __GLOBAL_CONFIG__.git) -> GitTag:
        """Create a GitTag instance from a string.

        Parameters
        ----------
        tag: str
            The Git tag string in the format '<prefix><major>.<minor>.<patch>'.
        config: GitConfig
            The Git configuration containing the expected prefix.

        Returns
        -------
        GitTag
            The GitTag instance created from the string.

        Raises
        ------
        GitTagError
            If the tag string does not start with the expected prefix.
            If the tag string is not in the correct format.

        """
        original_tag = tag

        prefix = config.tag_prefix

        if not tag.startswith(prefix):
            msg = (
                f"Tag '{original_tag}' does not start "
                f"with the expected prefix '{prefix}'"
            )
            raise GitTagError(msg)

        tag = tag.removeprefix(prefix)
        parts = tag.split(".")

        # TODO(97gamjak): implement support for different version schemes
        # https://97gamjak.atlassian.net/browse/DEV-49
        if len(parts) != 3:  # noqa: PLR2004 this will be removed and cleaned up with further naming schemes
            msg = f"Invalid tag format: {original_tag}"
            raise GitTagError(msg)

        try:
            major, minor, patch = map(int, parts)
        except ValueError as exc:
            msg = f"Invalid numeric components in tag: {original_tag}"
            raise GitTagError(msg) from exc
        return GitTag(major, minor, patch, prefix)


def get_all_tags(config: GitConfig = __GLOBAL_CONFIG__.git) -> list[GitTag]:
    """Get all Git tags in the repository.

    Parameters
    ----------
    config: GitConfig
        The Git configuration containing the expected prefix
        and empty tag list allowance.

    Returns
    -------
    list[GitTag]
        A list of all Git tags.

    Raises
    ------
    GitTagError
        If there is an error retrieving the Git tags and
        empty_tag_list_allowed is False.

    """
    empty_tag_list_allowed = config.empty_tag_list_allowed

    try:
        tags_output = subprocess.check_output(
            ["git", "tag", "--list"],
            stderr=subprocess.DEVNULL,
            text=True,
            shell=False,
        ).strip()
    except subprocess.CalledProcessError as e:
        msg = (
            "Error retrieving Git tags. "
            "Failed to execute git command. Command: 'git tag --list'"
        )
        raise GitTagError(msg) from e

    if not empty_tag_list_allowed and not tags_output:
        msg = "Failed to retrieve Git tags."
        raise GitTagError(msg)

    tags = []
    for tag_str in tags_output.splitlines():
        tag = GitTag.from_string(tag_str, config=config)
        tags.append(tag)

    return tags


def get_latest_tag(
    config: GitConfig = __GLOBAL_CONFIG__.git,
) -> GitTag:
    """Get the latest Git tag in the repository.

    Parameters
    ----------
    config: GitConfig
        The Git configuration containing the expected prefix
        and empty tag list allowance.

    Returns
    -------
    GitTag
        The latest Git tag. If no tags exist, returns GitTag(0, 0, 0, prefix).

    """
    tags = get_all_tags(config=config)
    if not tags:
        return GitTag(0, 0, 0, config.tag_prefix)

    return max(tags)
