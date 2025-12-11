"""Module for GitHub-related constants and functions."""

import os

__GITHUB_REPO__ = "https://github.com"
__MSTD_GITHUB_REPO__ = "https://github.com/97gamjak/mstd"
__MSTD_ISSUES_PAGE__ = f"{__MSTD_GITHUB_REPO__}/issues"


class MSTDGithubError(Exception):
    """Exception raised for GitHub-related errors in mstd checks."""

    def __init__(self, message: str) -> None:
        """Initialize the exception with a message."""
        super().__init__(f"MSTDGithubError: {message}")
        self.message = message


def get_github_repo() -> str:
    """Get the current GitHub repository URL.

    Returns
    -------
    str
        The GitHub repository URL.

    """
    repo = os.getenv("GITHUB_REPOSITORY", "repo/owner")
    # TODO(97gamjak): centralize env logic if needed elsewhere
    # https://github.com/97gamjak/mstd/issues/26

    return f"{__GITHUB_REPO__}/{repo}"
