"""Tests for devops.config.config module."""

from pathlib import Path

import pytest

from devops.config.config import (
    ConfigError,
    ExcludeConfig,
    GlobalConfig,
    parse_config,
    read_config,
)


def test_parse_config_with_exclude_configuration() -> None:
    """Test parsing exclude configurations from raw config."""
    raw_config = {
        "exclude": {
            "buggy_cpp_library_macros": ["MACRO1", "MACRO2", "MACRO3"],
        }
    }
    result = parse_config(raw_config)

    assert isinstance(result, GlobalConfig)
    assert isinstance(result.exclude, ExcludeConfig)
    assert result.exclude.buggy_cpp_library_macros == ["MACRO1", "MACRO2", "MACRO3"]


def test_parse_config_with_empty_exclude_list() -> None:
    """Test parsing exclude configurations with empty list."""
    raw_config = {
        "exclude": {
            "buggy_cpp_library_macros": [],
        }
    }
    result = parse_config(raw_config)

    assert isinstance(result, GlobalConfig)
    assert result.exclude.buggy_cpp_library_macros == []


def test_parse_config_missing_exclude_section() -> None:
    """Test handling missing 'exclude' key - should return defaults."""
    raw_config: dict[str, dict[str, list[str]]] = {}
    result = parse_config(raw_config)

    assert isinstance(result, GlobalConfig)
    assert result.exclude.buggy_cpp_library_macros == []


def test_parse_config_missing_buggy_cpp_library_macros_key() -> None:
    """Test missing 'buggy_cpp_library_macros' key returns empty list."""
    raw_config = {"exclude": {}}
    result = parse_config(raw_config)

    assert isinstance(result, GlobalConfig)
    assert result.exclude.buggy_cpp_library_macros == []


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


def test_parse_config_buggy_cpp_library_macros_not_list() -> None:
    """Test invalid type for buggy_cpp_library_macros raises error."""
    raw_config = {
        "exclude": {
            "buggy_cpp_library_macros": "not_a_list",
        }
    }

    with pytest.raises(ConfigError) as exc_info:
        parse_config(raw_config)

    assert "Expected list of strings for key" in str(exc_info.value)
    assert "buggy_cpp_library_macros" in str(exc_info.value)


def test_parse_config_buggy_cpp_library_macros_list_with_non_strings() -> None:
    """Test handling list with non-string elements - should raise ConfigError."""
    raw_config = {
        "exclude": {
            "buggy_cpp_library_macros": ["MACRO1", 42, "MACRO3"],
        }
    }

    with pytest.raises(ConfigError) as exc_info:
        parse_config(raw_config)

    assert "Expected list of strings for key" in str(exc_info.value)
    assert "buggy_cpp_library_macros" in str(exc_info.value)


def test_parse_config_buggy_cpp_library_macros_is_dict() -> None:
    """Test handling invalid data type when buggy_cpp_library_macros is a dict."""
    raw_config = {
        "exclude": {
            "buggy_cpp_library_macros": {"key": "value"},
        }
    }

    with pytest.raises(ConfigError) as exc_info:
        parse_config(raw_config)

    assert "Expected list of strings for key" in str(exc_info.value)
    assert "buggy_cpp_library_macros" in str(exc_info.value)


def test_read_config_with_none_path() -> None:
    """Test default configuration behavior when path is None."""
    result = read_config(None)

    assert isinstance(result, GlobalConfig)
    assert isinstance(result.exclude, ExcludeConfig)
    assert result.exclude.buggy_cpp_library_macros == []


def test_read_config_with_valid_toml_file(tmp_path: Path) -> None:
    """Test reading a valid TOML configuration file."""
    toml_content = """
[exclude]
buggy_cpp_library_macros = ["MACRO_A", "MACRO_B"]
"""

    toml_file = tmp_path / "config.toml"
    toml_file.write_text(toml_content)

    result = read_config(toml_file)

    assert isinstance(result, GlobalConfig)
    assert result.exclude.buggy_cpp_library_macros == ["MACRO_A", "MACRO_B"]


def test_read_config_with_path_object(tmp_path: Path) -> None:
    """Test reading configuration file using Path object."""
    toml_content = """
[exclude]
buggy_cpp_library_macros = ["TEST_MACRO"]
"""

    toml_file = tmp_path / "config.toml"
    toml_file.write_text(toml_content)

    result = read_config(toml_file)

    assert isinstance(result, GlobalConfig)
    assert result.exclude.buggy_cpp_library_macros == ["TEST_MACRO"]


def test_read_config_with_empty_toml_file(tmp_path: Path) -> None:
    """Test reading an empty TOML file - should return defaults."""
    toml_content = ""

    toml_file = tmp_path / "config.toml"
    toml_file.write_text(toml_content)

    result = read_config(toml_file)

    assert isinstance(result, GlobalConfig)
    assert result.exclude.buggy_cpp_library_macros == []


def test_read_config_with_partial_toml_file(tmp_path: Path) -> None:
    """Test reading TOML file with exclude section but no macros."""
    toml_content = """
[exclude]
"""

    toml_file = tmp_path / "config.toml"
    toml_file.write_text(toml_content)

    result = read_config(toml_file)

    assert isinstance(result, GlobalConfig)
    assert result.exclude.buggy_cpp_library_macros == []
