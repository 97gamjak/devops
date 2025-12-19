"""Module for reading and parsing configuration files."""

from __future__ import annotations

import typing
from dataclasses import dataclass, field
from pathlib import Path

from .toml import load_toml

if typing.TYPE_CHECKING:
    from typing import Any


# TODO(97gamjak): centralize exception handling
# https://github.com/97gamjak/devops/issues/24
class ConfigError(Exception):
    """Custom exception for configuration-related errors."""

    def __init__(self, message: str) -> None:
        """Initialize the exception with a message."""
        super().__init__(f"ConfigError: {message}")
        self.message = message


@dataclass(frozen=True)
class ExcludeConfig:
    """Dataclass to hold default exclusion values."""

    buggy_cpp_library_macros: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class GlobalConfig:
    """Dataclass to hold default configuration values."""

    exclude: ExcludeConfig = ExcludeConfig()


def _get_table(mapping: dict[str, Any], key: str) -> dict[str, Any]:
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


def _get_str_list(
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


def parse_config(raw: dict[str, Any]) -> GlobalConfig:
    """Parse a raw configuration dictionary into a GlobalConfig object.

    Parameters
    ----------
    raw: dict[str, Any]
        The raw configuration dictionary.

    Returns
    -------
    GlobalConfig
        The parsed GlobalConfig object.

    """
    exclude_table = _get_table(raw, "exclude")

    buggy_cpp_library_macros = _get_str_list(exclude_table, "buggy_cpp_library_macros")

    exclude_config = ExcludeConfig(
        buggy_cpp_library_macros=buggy_cpp_library_macros,
    )

    return GlobalConfig(exclude=exclude_config)


def read_config(path: str | Path | None = None) -> GlobalConfig:
    """Read and parse a TOML configuration file into a GlobalConfig object.

    Parameters
    ----------
    path: str | Path | None
        The path to the TOML configuration file.
        If None, defaults to the general default config

    Returns
    -------
    GlobalConfig
        The parsed GlobalConfig object.
    """
    # TODO(97gamjak): handle some internal global settings also in this class
    # which means we really need a different handling in here
    # https://97gamjak.atlassian.net/browse/DEV-46
    if path is None:
        return GlobalConfig()

    raw_config = load_toml(Path(path))
    return parse_config(raw_config)
