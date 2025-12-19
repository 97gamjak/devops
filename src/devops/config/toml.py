"""Module for handling TOML files in a DevOps context."""

from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any


# TODO(97gamjak): centralize exception handling
# https://github.com/97gamjak/devops/issues/24
class TomlError(Exception):
    """Custom exception for TOML-related errors."""

    def __init__(self, message: str) -> None:
        """Initialize the exception with a message."""
        super().__init__(f"TomlError: {message}")
        self.message = message


def load_toml(file_path: str | Path) -> dict[str, Any]:
    """Load a TOML file and return its contents as a dictionary.

    Parameters
    ----------
    file_path: str | Path
        The path to the TOML file to be loaded.

    Returns
    -------
    dict[str, Any]
        The contents of the TOML file as a dictionary.

    Raises
    ------
    TomlError
        If there is an error reading or parsing the TOML file.

    """
    if isinstance(file_path, str):
        file_path = Path(file_path)

    try:
        with file_path.open("rb") as toml_file:
            data = tomllib.load(toml_file)
    except (FileNotFoundError, tomllib.TOMLDecodeError) as e:
        msg = f"Error loading TOML file '{file_path}': {e}"
        raise TomlError(msg) from e

    if not isinstance(data, dict):
        msg = f"TOML file '{file_path}' does not contain a valid dictionary structure."
        raise TomlError(msg)

    return data
