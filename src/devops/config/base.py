"""Base configuration utilities."""

from __future__ import annotations

import typing

if typing.TYPE_CHECKING:
    from typing import Any

    from devops.enums import StrEnum


# TODO(97gamjak): centralize exception handling
# https://github.com/97gamjak/devops/issues/24
class ConfigError(Exception):
    """Custom exception for configuration-related errors."""

    def __init__(self, message: str) -> None:
        """Initialize the exception with a message."""
        super().__init__(f"ConfigError: {message}")
        self.message = message


def get_table(mapping: dict[str, Any], key: str) -> dict[str, Any]:
    """Get a sub-table from a mapping.

    Parameters
    ----------
    mapping: dict[str, Any]
        The mapping to extract the sub-table from.
    key: str
        The key of the sub-table.

    Returns
    -------
    dict[str, Any]
        The extracted sub-table or an empty dictionary if the key is not found.

    Raises
    ------
    ConfigError
        If the value associated with the key is not a dictionary.

    """
    value = mapping.get(key)

    if value is None:
        return {}

    if not isinstance(value, dict):
        msg = f"Expected dict for key '{key}', got {type(value).__name__}"
        raise ConfigError(msg)

    return value


def get_str_enum(
    mapping: dict[str, Any], key: str, enum_type: type, default: str | None = None
) -> StrEnum | None:
    """Get a string enum value from a mapping.

    Parameters
    ----------
    mapping: dict[str, Any]
        The mapping to extract the enum value from.
    key: str
        The key of the enum value.
    enum_type: type
        The enum type to validate against.
    default: str
        The default value to return if the key is not found.

    Returns
    -------
    StrEnum | None
        The extracted enum value or None if the key is not found.

    Raises
    ------
    ConfigError
        If the value associated with the key is not a valid enum value.
        If the value is not a string.
    """
    value = mapping.get(key, default)

    if value is None:
        return None

    if not isinstance(value, str):
        msg = f"Expected str for key '{key}', got {type(value).__name__}"
        raise ConfigError(msg)

    if enum_type.is_valid(value):
        return enum_type(value)

    msg = (
        f"Invalid value for key '{key}': {value},"
        f" expected one of {enum_type.list_values()}"
    )
    raise ConfigError(msg)


def get_str_list(
    mapping: dict[str, Any], key: str, default: list[str] | None = None
) -> list[str]:
    """Get a list of strings from a mapping.

    Parameters
    ----------
    mapping: dict[str, Any]
        The mapping to extract the list from.
    key: str
        The key of the list.
    default: list[str] | None
        The default value to return if the key is not found. Defaults to None.

    Returns
    -------
    list[str]
        The extracted list of strings or an empty list if the key is not found.

    Raises
    ------
    ConfigError
        If the value associated with the key is not a list of strings.

    """
    value = mapping.get(key, default)

    if value is None:
        return []

    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        msg = f"Expected list of strings for key '{key}', got {type(value).__name__}"
        raise ConfigError(msg)

    return value
