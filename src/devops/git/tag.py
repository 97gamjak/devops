"""Module for Git tag-related constants and functions."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass


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

    major: int = 0
    minor: int = 0
    patch: int = 0

    def __str__(self) -> str:
        """Return the string representation of the Git tag.

        Returns
        -------
        str
            The string representation of the Git tag
            in the format 'v<major>.<minor>.<patch>'.

        """
        return f"v{self.major}.{self.minor}.{self.patch}"

    @staticmethod
    def from_string(tag: str) -> GitTag:
        """Create a GitTag instance from a string.

        Parameters
        ----------
        tag: str
            The Git tag string in the format 'v<major>.<minor>.<patch>'.

        Returns
        -------
        GitTag
            The GitTag instance created from the string.

        Raises
        ------
        GitTagError
            If the tag string is not in the correct format.

        """
        original_tag = tag
        tag = tag.removeprefix("v")
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
        return GitTag(major, minor, patch)


def get_all_tags(*, empty_tag_list_allowed: bool = True) -> list[GitTag]:
    """Get all Git tags in the repository.

    Parameters
    ----------
    empty_tag_list_allowed: bool
        Whether to allow an empty tag list without raising an error.

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
    try:
        tags_output = subprocess.check_output(
            ["git", "tag", "--list"],
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
    except subprocess.CalledProcessError as e:
        if not empty_tag_list_allowed:
            msg = "Failed to retrieve Git tags."
            raise GitTagError(msg) from e
        return []

    tags = []
    for tag_str in tags_output.splitlines():
        tag = GitTag.from_string(tag_str)
        tags.append(tag)

    return tags


def get_latest_tag() -> GitTag:
    """Get the latest Git tag in the repository.

    Returns
    -------
    GitTag
        The latest Git tag. If no tags exist, returns GitTag(0, 0, 0).

    """
    tags = get_all_tags()
    if not tags:
        return GitTag(0, 0, 0)

    sorted_tags = sorted(tags, reverse=True)

    return sorted_tags[0]
