"""Module defining result types for mstd checks."""

from __future__ import annotations

from enum import Enum


class ResultTypeEnum(Enum):
    """Enumeration of result types for mstd checks."""

    Ok = "ok"
    Warning = "warning"
    Error = "error"


class ResultType:
    """Class representing the result of a mstd type check."""

    def __init__(self, value: ResultTypeEnum, description: str | None = None) -> None:
        """Initialize ResultType with a value and optional description."""
        self.value = value
        self.description = description
