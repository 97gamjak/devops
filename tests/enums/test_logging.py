"""Tests for devops.enums.logging module."""

import logging

from devops.enums.logging import LogLevel


def test_log_level_enum_values() -> None:
    """Test that all expected LogLevel enum values exist."""
    assert LogLevel.NONE.value == "NONE"
    assert LogLevel.DEBUG.value == "DEBUG"
    assert LogLevel.INFO.value == "INFO"
    assert LogLevel.WARNING.value == "WARNING"
    assert LogLevel.ERROR.value == "ERROR"
    assert LogLevel.CRITICAL.value == "CRITICAL"


def test_log_level_str_representation() -> None:
    """Test string representation of LogLevel members."""
    assert str(LogLevel.DEBUG) == "DEBUG"
    assert str(LogLevel.INFO) == "INFO"
    assert str(LogLevel.WARNING) == "WARNING"
    assert str(LogLevel.ERROR) == "ERROR"
    assert str(LogLevel.CRITICAL) == "CRITICAL"
    assert str(LogLevel.NONE) == "NONE"


def test_log_level_case_insensitive_access() -> None:
    """Test case-insensitive access to LogLevel members."""
    assert LogLevel("debug") == LogLevel.DEBUG
    assert LogLevel("DEBUG") == LogLevel.DEBUG
    assert LogLevel("Debug") == LogLevel.DEBUG
    assert LogLevel("info") == LogLevel.INFO
    assert LogLevel("INFO") == LogLevel.INFO


def test_log_level_from_int_with_valid_values() -> None:
    """Test from_int method with valid integer logging levels divided by 10."""
    assert LogLevel.from_int(0) == LogLevel.NONE
    assert LogLevel.from_int(1) == LogLevel.DEBUG
    assert LogLevel.from_int(2) == LogLevel.INFO
    assert LogLevel.from_int(3) == LogLevel.WARNING
    assert LogLevel.from_int(4) == LogLevel.ERROR
    assert LogLevel.from_int(5) == LogLevel.CRITICAL


def test_log_level_from_int_with_values_above_critical() -> None:
    """Test from_int method with values above CRITICAL returns CRITICAL."""
    assert LogLevel.from_int(6) == LogLevel.CRITICAL
    assert LogLevel.from_int(10) == LogLevel.CRITICAL
    assert LogLevel.from_int(100) == LogLevel.CRITICAL


def test_log_level_from_int_with_values_below_none() -> None:
    """Test from_int method with values below NONE returns NONE."""
    assert LogLevel.from_int(-1) == LogLevel.NONE
    assert LogLevel.from_int(-10) == LogLevel.NONE


def test_log_level_from_logging_level_with_standard_levels() -> None:
    """Test from_logging_level method with standard logging module levels."""
    assert LogLevel.from_logging_level(logging.NOTSET) == LogLevel.NONE
    assert LogLevel.from_logging_level(logging.DEBUG) == LogLevel.DEBUG
    assert LogLevel.from_logging_level(logging.INFO) == LogLevel.INFO
    assert LogLevel.from_logging_level(logging.WARNING) == LogLevel.WARNING
    assert LogLevel.from_logging_level(logging.ERROR) == LogLevel.ERROR
    assert LogLevel.from_logging_level(logging.CRITICAL) == LogLevel.CRITICAL


def test_log_level_from_logging_level_with_custom_values() -> None:
    """Test from_logging_level with custom integer values."""
    # Test with values that would be divided by 10
    assert LogLevel.from_logging_level(15) == LogLevel.DEBUG  # 15 // 10 = 1
    assert LogLevel.from_logging_level(25) == LogLevel.INFO  # 25 // 10 = 2
    assert LogLevel.from_logging_level(35) == LogLevel.WARNING  # 35 // 10 = 3
    assert LogLevel.from_logging_level(45) == LogLevel.ERROR  # 45 // 10 = 4
    assert LogLevel.from_logging_level(55) == LogLevel.CRITICAL  # 55 // 10 = 5


def test_log_level_to_logging_level() -> None:
    """Test to_logging_level method converts to correct logging module level."""
    assert LogLevel.NONE.to_logging_level() == logging.NOTSET
    assert LogLevel.DEBUG.to_logging_level() == logging.DEBUG
    assert LogLevel.INFO.to_logging_level() == logging.INFO
    assert LogLevel.WARNING.to_logging_level() == logging.WARNING
    assert LogLevel.ERROR.to_logging_level() == logging.ERROR
    assert LogLevel.CRITICAL.to_logging_level() == logging.CRITICAL


def test_log_level_comparison_less_than() -> None:
    """Test less than comparison operator."""
    assert LogLevel.NONE < LogLevel.DEBUG
    assert LogLevel.DEBUG < LogLevel.INFO
    assert LogLevel.INFO < LogLevel.WARNING
    assert LogLevel.WARNING < LogLevel.ERROR
    assert LogLevel.ERROR < LogLevel.CRITICAL

    assert not (LogLevel.DEBUG < LogLevel.NONE)
    assert not (LogLevel.INFO < LogLevel.DEBUG)
    assert not (LogLevel.DEBUG < LogLevel.DEBUG)


def test_log_level_comparison_less_than_or_equal() -> None:
    """Test less than or equal comparison operator."""
    assert LogLevel.NONE <= LogLevel.DEBUG
    assert LogLevel.DEBUG <= LogLevel.INFO
    assert LogLevel.INFO <= LogLevel.WARNING
    assert LogLevel.WARNING <= LogLevel.ERROR
    assert LogLevel.ERROR <= LogLevel.CRITICAL

    assert LogLevel.DEBUG <= LogLevel.DEBUG
    assert LogLevel.INFO <= LogLevel.INFO

    assert not (LogLevel.DEBUG <= LogLevel.NONE)
    assert not (LogLevel.INFO <= LogLevel.DEBUG)


def test_log_level_comparison_greater_than() -> None:
    """Test greater than comparison operator."""
    assert LogLevel.DEBUG > LogLevel.NONE
    assert LogLevel.INFO > LogLevel.DEBUG
    assert LogLevel.WARNING > LogLevel.INFO
    assert LogLevel.ERROR > LogLevel.WARNING
    assert LogLevel.CRITICAL > LogLevel.ERROR

    assert not (LogLevel.NONE > LogLevel.DEBUG)
    assert not (LogLevel.DEBUG > LogLevel.INFO)
    assert not (LogLevel.DEBUG > LogLevel.DEBUG)


def test_log_level_comparison_greater_than_or_equal() -> None:
    """Test greater than or equal comparison operator."""
    assert LogLevel.DEBUG >= LogLevel.NONE
    assert LogLevel.INFO >= LogLevel.DEBUG
    assert LogLevel.WARNING >= LogLevel.INFO
    assert LogLevel.ERROR >= LogLevel.WARNING
    assert LogLevel.CRITICAL >= LogLevel.ERROR

    assert LogLevel.DEBUG >= LogLevel.DEBUG
    assert LogLevel.INFO >= LogLevel.INFO

    assert not (LogLevel.NONE >= LogLevel.DEBUG)
    assert not (LogLevel.DEBUG >= LogLevel.INFO)


def test_log_level_comparison_equality() -> None:
    """Test equality comparison operator."""
    assert LogLevel.NONE == LogLevel.NONE
    assert LogLevel.DEBUG == LogLevel.DEBUG
    assert LogLevel.INFO == LogLevel.INFO
    assert LogLevel.WARNING == LogLevel.WARNING
    assert LogLevel.ERROR == LogLevel.ERROR
    assert LogLevel.CRITICAL == LogLevel.CRITICAL

    assert LogLevel.DEBUG != LogLevel.INFO
    assert LogLevel.INFO != LogLevel.WARNING
    assert LogLevel.NONE != LogLevel.DEBUG


def test_log_level_comparison_equality_with_non_log_level() -> None:
    """Test equality comparison with non-LogLevel objects."""
    assert LogLevel.INFO != "INFO"
    assert LogLevel.DEBUG != 10
    assert LogLevel.INFO != None  # noqa: E711
    assert LogLevel.INFO != 20


def test_log_level_hash() -> None:
    """Test that LogLevel instances are hashable."""
    level_set = {LogLevel.DEBUG, LogLevel.INFO, LogLevel.DEBUG}

    assert len(level_set) == 2
    assert LogLevel.DEBUG in level_set
    assert LogLevel.INFO in level_set


def test_log_level_can_be_used_as_dict_key() -> None:
    """Test that LogLevel can be used as dictionary keys."""
    level_dict = {
        LogLevel.DEBUG: "debug",
        LogLevel.INFO: "info",
        LogLevel.WARNING: "warning",
    }

    assert level_dict[LogLevel.DEBUG] == "debug"
    assert level_dict[LogLevel.INFO] == "info"
    assert level_dict[LogLevel.WARNING] == "warning"


def test_log_level_comparison_with_none_level() -> None:
    """Test that NONE level works correctly in comparisons."""
    assert LogLevel.NONE < LogLevel.DEBUG
    assert LogLevel.NONE < LogLevel.INFO
    assert LogLevel.NONE <= LogLevel.NONE
    assert LogLevel.NONE == LogLevel.NONE
    assert not (LogLevel.NONE > LogLevel.DEBUG)
    assert not (LogLevel.NONE >= LogLevel.DEBUG)


def test_log_level_roundtrip_conversion() -> None:
    """Test that conversion from LogLevel to int and back preserves value."""
    for level in [
        LogLevel.NONE,
        LogLevel.DEBUG,
        LogLevel.INFO,
        LogLevel.WARNING,
        LogLevel.ERROR,
        LogLevel.CRITICAL,
    ]:
        logging_level = level.to_logging_level()
        converted_back = LogLevel.from_logging_level(logging_level)
        assert converted_back == level
