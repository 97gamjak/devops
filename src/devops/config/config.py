"""Module for reading and parsing configuration files."""

from __future__ import annotations

import typing
from dataclasses import dataclass, field
from pathlib import Path

from devops.logger import config_logger

from .base import get_str_list, get_table
from .config_cpp import CppConfig, parse_cpp_config
from .config_file import FileConfig, parse_file_config
from .config_git import GitConfig, parse_git_config
from .config_logging import LoggingConfig, parse_logging_config
from .constants import Constants
from .toml import load_toml

if typing.TYPE_CHECKING:
    from typing import Any


@dataclass
class ExcludeConfig:
    """Dataclass to hold default exclusion values."""

    buggy_cpp_library_macros: list[str] = field(default_factory=list)


@dataclass
class GlobalConfig:
    """Dataclass to hold default configuration values."""

    exclude: ExcludeConfig = field(default_factory=ExcludeConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    git: GitConfig = field(default_factory=GitConfig)
    cpp: CppConfig = field(default_factory=CppConfig)
    file: FileConfig = field(default_factory=FileConfig)


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
    # start logging configuration
    # NOTE: this should be done before anything else
    # as logging config already updates loggers
    logging_config = parse_logging_config(raw)

    git_config = parse_git_config(raw)
    cpp_config = parse_cpp_config(raw)
    file_config = parse_file_config(raw)

    # start exclude configuration
    exclude_table = get_table(raw, "exclude")

    buggy_cpp_library_macros = get_str_list(exclude_table, "buggy_cpp_library_macros")

    exclude_config = ExcludeConfig(
        buggy_cpp_library_macros=buggy_cpp_library_macros,
    )
    # end exclude configuration

    return GlobalConfig(
        exclude=exclude_config,
        logging=logging_config,
        git=git_config,
        cpp=cpp_config,
        file=file_config,
    )


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
    if path is None:
        return GlobalConfig()

    raw_config = load_toml(Path(path))
    return parse_config(raw_config)


def init_config() -> GlobalConfig:
    """Initialize global config paths.

    Returns
    -------
    GlobalConfig
        The initialized global configuration object.
    """
    file_names = Constants.files.toml_filenames
    found_configs = [Path(fname) for fname in file_names if Path(fname).is_file()]

    if len(found_configs) == 1:
        config = read_config(Path(found_configs[0]))
    else:
        config = read_config()

    # Note: we log here after setting up the config to ensure logging config is applied
    # before any logging is done.

    use_default_config = False

    if len(found_configs) > 1:
        config_logger.warning(
            "Multiple config files found: %s. Using no config file.",
            ", ".join(str(p) for p in found_configs),
        )
        use_default_config = True
    elif len(found_configs) < 1:
        config_logger.debug("No config file found. Using default configuration.")
        use_default_config = True

    if use_default_config:
        config_logger.info("The default configuration being used is: %s", config)

    return config
