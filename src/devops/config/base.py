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


def _get_type(
    mapping: dict[str, Any], key: str, default: Any, expected_type: type
) -> Any:
    """Get a value of expected type from a mapping.

    Parameters
    ----------
    mapping: dict[str, Any]
        The mapping to extract the value from.
    key: str
        The key of the value.
    default: Any
        The default value to return if the key is not found.
    expected_type: type
        The expected type of the value.

    Returns
    -------
    Any
        The extracted value or the default value if the key is not found.

    Raises
    ------
    ConfigError
        If the value associated with the key is not of the expected type.
    """
    value = mapping.get(key, default)

    if value is None:
        return None

    if not isinstance(value, expected_type):
        msg = (
            f"Expected {expected_type.__name__} for "
            f"key '{key}', got {type(value).__name__}"
        )
        raise ConfigError(msg)

    return value


def get_bool(
    mapping: dict[str, Any], key: str, *, default: bool | None = None
) -> bool | None:
    """Get a boolean value from a mapping.

    Parameters
    ----------
    mapping: dict[str, Any]
        The mapping to extract the boolean from.
    key: str
        The key of the boolean.
    default: bool | None
        The default value to return if the key is not found.

    Returns
    -------
    bool | None
        The extracted boolean value or None if the key is not found.
    """
    return _get_type(mapping, key, default, bool)


def get_str(
    mapping: dict[str, Any], key: str, default: str | None = None
) -> str | None:
    """Get a string value from a mapping.

    Parameters
    ----------
    mapping: dict[str, Any]
        The mapping to extract the string from.
    key: str
        The key of the string.
    default: str | None
        The default value to return if the key is not found.

    Returns
    -------
    str | None
        The extracted string value or None if the key is not found.
    """
    return _get_type(mapping, key, default, str)


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
    """
    value = _get_type(mapping, key, default, str)

    if value is None:
        return None

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
