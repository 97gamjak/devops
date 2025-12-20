"""Module for logging configuration."""

import logging
from dataclasses import dataclass

from devops.enums import LogLevel
from devops.logger import config_logger, cpp_check_logger, utils_logger

from .base import get_str_enum, get_table


@dataclass
class LoggingConfig:
    """Dataclass to hold logging configuration values."""

    global_level: LogLevel = LogLevel.INFO
    utils_level: LogLevel = LogLevel.INFO
    config_level: LogLevel = LogLevel.INFO
    cpp_level: LogLevel = LogLevel.INFO

    def to_toml_lines(self) -> list[str]:
        """Convert the LoggingConfig to TOML lines.

        Returns
        -------
        list[str]
            The list of TOML lines representing the configuration.

        """
        lines = ["[logging]\n"]
        lines.append(f'#global_level = "{self.global_level.value}"\n')
        lines.append(f'#utils_level = "{self.utils_level.value}"\n')
        lines.append(f'#config_level = "{self.config_level.value}"\n')
        lines.append(f'#cpp_level = "{self.cpp_level.value}"\n')
        return lines


def parse_logging_config(raw_config: dict) -> LoggingConfig:
    """Parse logging configuration from a raw dictionary.

    As a side effect, this function sets the logging levels
    according to the parsed configuration.

    Parameters
    ----------
    raw_config: dict
        The raw logging configuration dictionary.

    Returns
    -------
    LoggingConfig
        The parsed LoggingConfig dataclass instance.

    """
    table = get_table(raw_config, "logging")

    global_level = get_str_enum(table, "global_level", LogLevel)
    utils_level = get_str_enum(table, "utils_level", LogLevel)
    config_level = get_str_enum(table, "config_level", LogLevel)
    cpp_level = get_str_enum(table, "cpp_level", LogLevel)

    if global_level is None:
        global_level = LogLevel.from_logging_level(logging.root.level)

    if utils_level is None:
        utils_level = LogLevel.from_logging_level(utils_logger.level)

    if config_level is None:
        config_level = LogLevel.from_logging_level(config_logger.level)

    if cpp_level is None:
        cpp_level = LogLevel.from_logging_level(cpp_check_logger.level)

    config = LoggingConfig(
        global_level=global_level,
        utils_level=utils_level,
        config_level=config_level,
        cpp_level=cpp_level,
    )

    set_logging_levels(config)
    return config


def set_logging_levels(config: LoggingConfig) -> None:
    """Set logging levels based on the provided LoggingConfig.

    Parameters
    ----------
    config: LoggingConfig
        The logging configuration.

    """
    logging.getLogger().setLevel(config.global_level.to_logging_level())
    utils_logger.setLevel(config.utils_level.to_logging_level())
    config_logger.setLevel(config.config_level.to_logging_level())
    cpp_check_logger.setLevel(config.cpp_level.to_logging_level())
