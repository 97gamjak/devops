"""Module for GitHub-related constants and functions."""

__GITHUB_REPO__ = "https://github.com"
__MSTD_GITHUB_REPO__ = "https://github.com/97gamjak/mstd"
__MSTD_ISSUES_PAGE__ = f"{__MSTD_GITHUB_REPO__}/issues"


class MSTDGithubError(Exception):
    """Exception raised for GitHub-related errors in mstd checks."""

    def __init__(self, message: str) -> None:
        """Initialize the exception with a message."""
        super().__init__(f"MSTDGithubError: {message}")
        self.message = message
