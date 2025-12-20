"""Module defining logging level enumeration."""

from __future__ import annotations

import logging

from .base import StrEnum


class LogLevel(StrEnum):
    """Enumeration of logging levels."""

    NONE = "NONE"
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

    @classmethod
    def from_int(cls, level: int) -> LogLevel:
        """Create LogLevel from an integer logging level.

        Parameters
        ----------
        level: int
            The integer logging level.

        Returns
        -------
        LogLevel
            The corresponding LogLevel enumeration member.

        """
        int_to_level = {
            logging.DEBUG // 10: cls.DEBUG,
            logging.INFO // 10: cls.INFO,
            logging.WARNING // 10: cls.WARNING,
            logging.ERROR // 10: cls.ERROR,
            logging.CRITICAL // 10: cls.CRITICAL,
        }
        if level in int_to_level:
            return int_to_level[level]

        if level > logging.CRITICAL // 10:
            return cls.CRITICAL

        if level < logging.DEBUG // 10:
            return cls.DEBUG

        return cls.INFO

    def to_logging_level(self) -> int:
        """Convert LogLevel to corresponding logging module level.

        Returns
        -------
        int
            The logging module level.

        """
        level_mapping = {
            LogLevel.DEBUG: logging.DEBUG,
            LogLevel.INFO: logging.INFO,
            LogLevel.WARNING: logging.WARNING,
            LogLevel.ERROR: logging.ERROR,
            LogLevel.CRITICAL: logging.CRITICAL,
        }
        return level_mapping[self]

    @classmethod
    def from_logging_level(cls, level: int) -> LogLevel:
        """Create LogLevel from an integer logging level.

        Parameters
        ----------
        level: int
            The integer logging level.

        Returns
        -------
        LogLevel
            The corresponding LogLevel enumeration member.

        """
        return cls.from_int(level // 10)

    def __lt__(self, other: LogLevel) -> bool:
        """Compare two LogLevel instances.

        Parameters
        ----------
        other: LogLevel
            The other LogLevel instance to compare with.

        Returns
        -------
        bool
            True if this LogLevel is less than the other LogLevel, False otherwise.

        """
        return self.to_logging_level() < other.to_logging_level()

    def __le__(self, other: LogLevel) -> bool:
        """Check if this LogLevel is less than or equal to another LogLevel.

        Parameters
        ----------
        other: LogLevel
            The other LogLevel instance to compare with.

        Returns
        -------
        bool
            True if this LogLevel is less than or equal to the other LogLevel,
            False otherwise.

        """
        return self.to_logging_level() <= other.to_logging_level()

    def __gt__(self, other: LogLevel) -> bool:
        """Check if this LogLevel is greater than another LogLevel.

        Parameters
        ----------
        other: LogLevel
            The other LogLevel instance to compare with.

        Returns
        -------
        bool
            True if this LogLevel is greater than the other LogLevel,
            False otherwise.

        """
        return self.to_logging_level() > other.to_logging_level()

    def __ge__(self, other: LogLevel) -> bool:
        """Check if this LogLevel is greater than or equal to another LogLevel.

        Parameters
        ----------
        other: LogLevel
            The other LogLevel instance to compare with.

        Returns
        -------
        bool
            True if this LogLevel is greater than or equal to the other LogLevel,
            False otherwise.

        """
        return self.to_logging_level() >= other.to_logging_level()

    def __eq__(self, other: object) -> bool:
        """Check if this LogLevel is equal to another LogLevel.

        Parameters
        ----------
        other: object
            The other object to compare with.

        Returns
        -------
        bool
            True if this LogLevel is equal to the other LogLevel,
            False otherwise.

        """
        if not isinstance(other, LogLevel):
            return NotImplemented
        return self.to_logging_level() == other.to_logging_level()

    def __hash__(self) -> int:
        """Return the hash of the LogLevel instance.

        Returns
        -------
        int
            The hash value of the LogLevel instance.

        """
        return hash(self.value)
