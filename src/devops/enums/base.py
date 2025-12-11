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
