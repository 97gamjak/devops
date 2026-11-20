"""Errors raised by the release tooling."""


class ReleaseError(Exception):
    """Exception raised when a release step cannot continue safely."""

    def __init__(self, message: str) -> None:
        """Initialize the exception with a message."""
        super().__init__(message)
        self.message = message
