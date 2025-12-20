"""Tests for devops.config.logging_config module."""

import logging
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from devops.config.base import ConfigError
from devops.config.logging_config import (
    LoggingConfig,
    parse_logging_config,
    set_logging_levels,
)
from devops.enums import LogLevel


def test_logging_config_dataclass_defaults() -> None:
    """Test LoggingConfig dataclass default values."""
    config = LoggingConfig()

    assert config.global_level == LogLevel.INFO
    assert config.utils_level == LogLevel.INFO
    assert config.config_level == LogLevel.INFO
    assert config.cpp_level == LogLevel.INFO


def test_logging_config_dataclass_with_custom_values() -> None:
    """Test LoggingConfig dataclass with custom values."""
    config = LoggingConfig(
        global_level=LogLevel.DEBUG,
        utils_level=LogLevel.WARNING,
        config_level=LogLevel.ERROR,
        cpp_level=LogLevel.CRITICAL,
    )

    assert config.global_level == LogLevel.DEBUG
    assert config.utils_level == LogLevel.WARNING
    assert config.config_level == LogLevel.ERROR
    assert config.cpp_level == LogLevel.CRITICAL


def test_parse_logging_config_with_all_levels() -> None:
    """Test parse_logging_config with all logging levels specified."""
    raw_config = {
        "logging": {
            "global_level": "DEBUG",
            "utils_level": "INFO",
            "config_level": "WARNING",
            "cpp_level": "ERROR",
        }
    }

    with patch("devops.config.logging_config.set_logging_levels"):
        config = parse_logging_config(raw_config)

    assert config.global_level == LogLevel.DEBUG
    assert config.utils_level == LogLevel.INFO
    assert config.config_level == LogLevel.WARNING
    assert config.cpp_level == LogLevel.ERROR


def test_parse_logging_config_with_case_insensitive_levels() -> None:
    """Test parse_logging_config with case-insensitive level values."""
    raw_config = {
        "logging": {
            "global_level": "debug",
            "utils_level": "Info",
            "config_level": "WARNING",
            "cpp_level": "error",
        }
    }

    with patch("devops.config.logging_config.set_logging_levels"):
        config = parse_logging_config(raw_config)

    assert config.global_level == LogLevel.DEBUG
    assert config.utils_level == LogLevel.INFO
    assert config.config_level == LogLevel.WARNING
    assert config.cpp_level == LogLevel.ERROR


def test_parse_logging_config_with_missing_logging_section() -> None:
    """Test parse_logging_config with missing logging section uses defaults."""
    raw_config: dict = {}

    with patch("devops.config.logging_config.set_logging_levels"):
        with patch("logging.root.level", logging.INFO):
            with patch("devops.config.logging_config.utils_logger.level", logging.INFO):
                with patch(
                    "devops.config.logging_config.config_logger.level", logging.INFO
                ):
                    with patch(
                        "devops.config.logging_config.cpp_check_logger.level",
                        logging.INFO,
                    ):
                        config = parse_logging_config(raw_config)

    assert config.global_level == LogLevel.INFO
    assert config.utils_level == LogLevel.INFO
    assert config.config_level == LogLevel.INFO
    assert config.cpp_level == LogLevel.INFO


def test_parse_logging_config_with_partial_levels() -> None:
    """Test parse_logging_config with only some levels specified."""
    raw_config = {
        "logging": {
            "global_level": "DEBUG",
            "cpp_level": "ERROR",
        }
    }

    with patch("devops.config.logging_config.set_logging_levels"):
        with patch("devops.config.logging_config.utils_logger.level", logging.WARNING):
            with patch(
                "devops.config.logging_config.config_logger.level", logging.ERROR
            ):
                config = parse_logging_config(raw_config)

    assert config.global_level == LogLevel.DEBUG
    assert config.utils_level == LogLevel.WARNING
    assert config.config_level == LogLevel.ERROR
    assert config.cpp_level == LogLevel.ERROR


def test_parse_logging_config_with_invalid_level() -> None:
    """Test parse_logging_config with invalid logging level raises ConfigError."""
    raw_config = {
        "logging": {
            "global_level": "INVALID_LEVEL",
        }
    }

    with pytest.raises(ConfigError) as exc_info:
        parse_logging_config(raw_config)

    assert "Invalid value for key 'global_level'" in str(exc_info.value)
    assert "INVALID_LEVEL" in str(exc_info.value)


def test_parse_logging_config_with_non_string_level() -> None:
    """Test parse_logging_config with non-string level value raises ConfigError."""
    raw_config = {
        "logging": {
            "global_level": 10,
        }
    }

    with pytest.raises(ConfigError) as exc_info:
        parse_logging_config(raw_config)

    assert "Expected str for key 'global_level'" in str(exc_info.value)
    assert "got int" in str(exc_info.value)


def test_parse_logging_config_with_logging_section_not_dict() -> None:
    """Test parse_logging_config with logging section not a dict raises ConfigError."""
    raw_config = {"logging": "not_a_dict"}

    with pytest.raises(ConfigError) as exc_info:
        parse_logging_config(raw_config)

    assert "Expected dict for key 'logging'" in str(exc_info.value)
    assert "got str" in str(exc_info.value)


def test_parse_logging_config_calls_set_logging_levels() -> None:
    """Test parse_logging_config calls set_logging_levels as side effect."""
    raw_config = {
        "logging": {
            "global_level": "DEBUG",
        }
    }

    with patch(
        "devops.config.logging_config.set_logging_levels"
    ) as mock_set_levels:
        with patch("devops.config.logging_config.utils_logger.level", logging.INFO):
            with patch("devops.config.logging_config.config_logger.level", logging.INFO):
                with patch(
                    "devops.config.logging_config.cpp_check_logger.level", logging.INFO
                ):
                    config = parse_logging_config(raw_config)

        mock_set_levels.assert_called_once()
        call_args = mock_set_levels.call_args[0][0]
        assert call_args.global_level == LogLevel.DEBUG


def test_set_logging_levels_sets_global_level() -> None:
    """Test set_logging_levels sets the root logger level."""
    config = LoggingConfig(global_level=LogLevel.DEBUG)

    with patch("logging.getLogger") as mock_get_logger:
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        with patch("devops.config.logging_config.utils_logger") as mock_utils:
            with patch("devops.config.logging_config.config_logger") as mock_config:
                with patch("devops.config.logging_config.cpp_check_logger") as mock_cpp:
                    set_logging_levels(config)

        mock_logger.setLevel.assert_called_once_with(logging.DEBUG)


def test_set_logging_levels_sets_all_logger_levels() -> None:
    """Test set_logging_levels sets all logger levels correctly."""
    config = LoggingConfig(
        global_level=LogLevel.DEBUG,
        utils_level=LogLevel.INFO,
        config_level=LogLevel.WARNING,
        cpp_level=LogLevel.ERROR,
    )

    with patch("logging.getLogger") as mock_get_logger:
        mock_root = MagicMock()
        mock_get_logger.return_value = mock_root

        with patch("devops.config.logging_config.utils_logger") as mock_utils:
            with patch("devops.config.logging_config.config_logger") as mock_config:
                with patch("devops.config.logging_config.cpp_check_logger") as mock_cpp:
                    set_logging_levels(config)

        mock_root.setLevel.assert_called_once_with(logging.DEBUG)
        mock_utils.setLevel.assert_called_once_with(logging.INFO)
        mock_config.setLevel.assert_called_once_with(logging.WARNING)
        mock_cpp.setLevel.assert_called_once_with(logging.ERROR)


def test_parse_logging_config_with_none_level() -> None:
    """Test parse_logging_config with NONE level."""
    raw_config = {
        "logging": {
            "global_level": "NONE",
        }
    }

    with patch("devops.config.logging_config.set_logging_levels"):
        with patch("devops.config.logging_config.utils_logger.level", logging.INFO):
            with patch("devops.config.logging_config.config_logger.level", logging.INFO):
                with patch(
                    "devops.config.logging_config.cpp_check_logger.level", logging.INFO
                ):
                    config = parse_logging_config(raw_config)

    assert config.global_level == LogLevel.NONE


def test_set_logging_levels_with_none_level() -> None:
    """Test set_logging_levels correctly converts NONE to NOTSET."""
    config = LoggingConfig(global_level=LogLevel.NONE)

    with patch("logging.getLogger") as mock_get_logger:
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        with patch("devops.config.logging_config.utils_logger") as mock_utils:
            with patch("devops.config.logging_config.config_logger") as mock_config:
                with patch("devops.config.logging_config.cpp_check_logger") as mock_cpp:
                    set_logging_levels(config)

        mock_logger.setLevel.assert_called_once_with(logging.NOTSET)
