"""Base enumerations for mstd checks."""

from __future__ import annotations

from enum import Enum


class StrEnum(Enum):
    """Base class for string enumerations."""

    def __str__(self) -> str:
        """Return the string representation of the enumeration value."""
        return self.value.upper()

    @classmethod
    def _missing_(cls, value: object) -> StrEnum | None:
        """Handle missing enumeration values in a case-insensitive manner."""
        if isinstance(value, str):
            for member in cls:
                if member.value.upper() == value.upper():
                    return member
        return None

    @classmethod
    def is_valid(cls, value: str) -> bool:
        """Check if a given string is a valid enumeration member.

        Parameters
        ----------
        value: str
            The string to check.

        Returns
        -------
        bool
            True if the string corresponds to a valid enumeration member,
            False otherwise.

        """
        try:
            cls(value)
        except ValueError:
            return False

        return True

    @classmethod
    def list_values(cls) -> list[str]:
        """List all enumeration values as strings.

        Returns
        -------
        list[str]
            A list of all enumeration values.

        """
        return [member.value for member in cls]
