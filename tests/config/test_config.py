"""Tests for devops.config.config module."""

from pathlib import Path

import pytest

from devops.config.base import ConfigError, get_str_enum
from devops.config.config import (
    ExcludeConfig,
    GlobalConfig,
    parse_config,
    read_config,
)
from devops.enums import LogLevel


def test_parse_config_with_exclude_configuration() -> None:
    """Test parsing exclude configurations from raw config."""
    raw_config = {
        "exclude": {
            "buggy_cpp_macros": ["MACRO1", "MACRO2", "MACRO3"],
        }
    }
    result = parse_config(raw_config)

    assert isinstance(result, GlobalConfig)
    assert isinstance(result.exclude, ExcludeConfig)
    assert result.exclude.buggy_cpp_macros == ["MACRO1", "MACRO2", "MACRO3"]


def test_parse_config_with_empty_exclude_list() -> None:
    """Test parsing exclude configurations with empty list."""
    raw_config = {
        "exclude": {
            "buggy_cpp_macros": [],
        }
    }
    result = parse_config(raw_config)

    assert isinstance(result, GlobalConfig)
    assert result.exclude.buggy_cpp_macros == []


def test_parse_config_missing_exclude_section() -> None:
    """Test handling missing 'exclude' key - should return defaults."""
    raw_config: dict[str, dict[str, list[str]]] = {}
    result = parse_config(raw_config)

    assert isinstance(result, GlobalConfig)
    assert result.exclude.buggy_cpp_macros == []


def test_parse_config_missing_buggy_cpp_macros_key() -> None:
    """Test missing 'buggy_cpp_macros' key returns empty list."""
    raw_config = {"exclude": {}}
    result = parse_config(raw_config)

    assert isinstance(result, GlobalConfig)
    assert result.exclude.buggy_cpp_macros == []


def test_parse_config_exclude_not_dict() -> None:
    """Test handling invalid data type for 'exclude' - should raise ConfigError."""
    raw_config = {"exclude": "not_a_dict"}

    with pytest.raises(ConfigError) as exc_info:
        parse_config(raw_config)

    assert "Expected dict for key 'exclude'" in str(exc_info.value)
    assert "got str" in str(exc_info.value)


def test_parse_config_exclude_is_list() -> None:
    """Test invalid data type when exclude is a list raises error."""
    raw_config = {"exclude": ["item1", "item2"]}

    with pytest.raises(ConfigError) as exc_info:
        parse_config(raw_config)

    assert "Expected dict for key 'exclude'" in str(exc_info.value)
    assert "got list" in str(exc_info.value)


def test_parse_config_buggy_cpp_macros_not_list() -> None:
    """Test invalid type for buggy_cpp_macros raises error."""
    raw_config = {
        "exclude": {
            "buggy_cpp_macros": "not_a_list",
        }
    }

    with pytest.raises(ConfigError) as exc_info:
        parse_config(raw_config)

    assert "Expected list of strings for key" in str(exc_info.value)
    assert "buggy_cpp_macros" in str(exc_info.value)


def test_parse_config_buggy_cpp_macros_list_with_non_strings() -> None:
    """Test handling list with non-string elements - should raise ConfigError."""
    raw_config = {
        "exclude": {
            "buggy_cpp_macros": ["MACRO1", 42, "MACRO3"],
        }
    }

    with pytest.raises(ConfigError) as exc_info:
        parse_config(raw_config)

    assert "Expected list of strings for key" in str(exc_info.value)
    assert "buggy_cpp_macros" in str(exc_info.value)


def test_parse_config_buggy_cpp_macros_is_dict() -> None:
    """Test handling invalid data type when buggy_cpp_macros is a dict."""
    raw_config = {
        "exclude": {
            "buggy_cpp_macros": {"key": "value"},
        }
    }

    with pytest.raises(ConfigError) as exc_info:
        parse_config(raw_config)

    assert "Expected list of strings for key" in str(exc_info.value)
    assert "buggy_cpp_macros" in str(exc_info.value)


def test_read_config_with_none_path() -> None:
    """Test default configuration behavior when path is None."""
    result = read_config(None)

    assert isinstance(result, GlobalConfig)
    assert isinstance(result.exclude, ExcludeConfig)
    assert result.exclude.buggy_cpp_macros == []


def test_read_config_with_valid_toml_file(tmp_path: Path) -> None:
    """Test reading a valid TOML configuration file."""
    toml_content = """
[exclude]
buggy_cpp_macros = ["MACRO_A", "MACRO_B"]
"""

    toml_file = tmp_path / "config.toml"
    toml_file.write_text(toml_content)

    result = read_config(toml_file)

    assert isinstance(result, GlobalConfig)
    assert result.exclude.buggy_cpp_macros == ["MACRO_A", "MACRO_B"]


def test_read_config_with_path_object(tmp_path: Path) -> None:
    """Test reading configuration file using Path object."""
    toml_content = """
[exclude]
buggy_cpp_macros = ["TEST_MACRO"]
"""

    toml_file = tmp_path / "config.toml"
    toml_file.write_text(toml_content)

    result = read_config(toml_file)

    assert isinstance(result, GlobalConfig)
    assert result.exclude.buggy_cpp_macros == ["TEST_MACRO"]


def test_read_config_with_empty_toml_file(tmp_path: Path) -> None:
    """Test reading an empty TOML file - should return defaults."""
    toml_content = ""

    toml_file = tmp_path / "config.toml"
    toml_file.write_text(toml_content)

    result = read_config(toml_file)

    assert isinstance(result, GlobalConfig)
    assert result.exclude.buggy_cpp_macros == []


def test_read_config_with_partial_toml_file(tmp_path: Path) -> None:
    """Test reading TOML file with exclude section but no macros."""
    toml_content = """
[exclude]
"""

    toml_file = tmp_path / "config.toml"
    toml_file.write_text(toml_content)

    result = read_config(toml_file)

    assert isinstance(result, GlobalConfig)
    assert result.exclude.buggy_cpp_macros == []


def test_get_str_enum_with_valid_value() -> None:
    """Test get_str_enum with valid enum value."""
    mapping = {"level": "INFO"}

    result = get_str_enum(mapping, "level", LogLevel)

    assert result == LogLevel.INFO


def test_get_str_enum_with_valid_case_insensitive_value() -> None:
    """Test get_str_enum with case-insensitive enum value."""
    mapping = {"level": "info"}

    result = get_str_enum(mapping, "level", LogLevel)

    assert result == LogLevel.INFO


def test_get_str_enum_with_missing_key() -> None:
    """Test get_str_enum with missing key returns None."""
    mapping = {"other_key": "value"}

    result = get_str_enum(mapping, "level", LogLevel)

    assert result is None


def test_get_str_enum_with_default_value() -> None:
    """Test get_str_enum with default value when key is missing."""
    mapping = {"other_key": "value"}

    result = get_str_enum(mapping, "level", LogLevel, default="DEBUG")

    assert result == LogLevel.DEBUG


def test_get_str_enum_with_invalid_enum_value() -> None:
    """Test get_str_enum with invalid enum value raises ConfigError."""
    mapping = {"level": "INVALID"}

    with pytest.raises(ConfigError) as exc_info:
        get_str_enum(mapping, "level", LogLevel)

    assert "Invalid value for key 'level': INVALID" in str(exc_info.value)
    assert "expected one of" in str(exc_info.value)


def test_get_str_enum_with_non_string_value() -> None:
    """Test get_str_enum with non-string value raises ConfigError."""
    mapping = {"level": 123}

    with pytest.raises(ConfigError) as exc_info:
        get_str_enum(mapping, "level", LogLevel)

    assert "Expected str for key 'level'" in str(exc_info.value)
    assert "got int" in str(exc_info.value)


def test_get_str_enum_with_none_value() -> None:
    """Test get_str_enum with None value returns None."""
    mapping = {"level": None}

    result = get_str_enum(mapping, "level", LogLevel)

    assert result is None


def test_get_str_enum_with_list_value() -> None:
    """Test get_str_enum with list value raises ConfigError."""
    mapping = {"level": ["INFO", "DEBUG"]}

    with pytest.raises(ConfigError) as exc_info:
        get_str_enum(mapping, "level", LogLevel)

    assert "Expected str for key 'level'" in str(exc_info.value)
    assert "got list" in str(exc_info.value)


def test_get_str_enum_with_dict_value() -> None:
    """Test get_str_enum with dict value raises ConfigError."""
    mapping = {"level": {"nested": "INFO"}}

    with pytest.raises(ConfigError) as exc_info:
        get_str_enum(mapping, "level", LogLevel)

    assert "Expected str for key 'level'" in str(exc_info.value)
    assert "got dict" in str(exc_info.value)
