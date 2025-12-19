"""Tests for devops.config.toml module."""

from __future__ import annotations

import typing

import pytest

from devops.config.toml import TomlError, load_toml

if typing.TYPE_CHECKING:
    from pathlib import Path


def test_load_toml_success(tmp_path: Path) -> None:
    """Test successful TOML loading with valid file."""
    # Create a valid TOML file
    toml_file = tmp_path / "test_config.toml"
    toml_content = """
[database]
server = "192.168.1.1"
ports = [8000, 8001, 8002]
connection_max = 5000
enabled = true

[servers]
alpha = "10.0.0.1"
beta = "10.0.0.2"
"""
    toml_file.write_text(toml_content)

    # Load the TOML file
    result = load_toml(toml_file)

    # Assert the structure is correct
    assert isinstance(result, dict)
    assert "database" in result
    assert "servers" in result
    assert result["database"]["server"] == "192.168.1.1"
    assert result["database"]["ports"] == [8000, 8001, 8002]
    assert result["database"]["connection_max"] == 5000
    assert result["database"]["enabled"] is True
    assert result["servers"]["alpha"] == "10.0.0.1"
    assert result["servers"]["beta"] == "10.0.0.2"


def test_load_toml_string_path(tmp_path: Path) -> None:
    """Test that load_toml converts string path to Path object."""
    # Create a valid TOML file
    toml_file = tmp_path / "test_config.toml"
    toml_content = """
[app]
name = "TestApp"
version = "1.0.0"
"""
    toml_file.write_text(toml_content)

    # Load using string path instead of Path object
    result = load_toml(str(toml_file))

    # Assert the structure is correct
    assert isinstance(result, dict)
    assert "app" in result
    assert result["app"]["name"] == "TestApp"
    assert result["app"]["version"] == "1.0.0"


def test_load_toml_file_not_found(tmp_path: Path) -> None:
    """Test handling of FileNotFoundError for missing files."""
    non_existent_file = tmp_path / "non_existent_file.toml"

    # Assert that TomlError is raised
    with pytest.raises(TomlError) as exc_info:
        load_toml(non_existent_file)

    # Verify the error message contains the file path
    assert "non_existent_file.toml" in str(exc_info.value)
    assert "Error loading TOML file" in str(exc_info.value)


def test_load_toml_invalid_syntax(tmp_path: Path) -> None:
    """Test handling of TOMLDecodeError for invalid TOML syntax."""
    # Create a file with invalid TOML syntax
    toml_file = tmp_path / "invalid.toml"
    invalid_content = """
[database
server = "192.168.1.1"
"""
    toml_file.write_text(invalid_content)

    # Assert that TomlError is raised
    with pytest.raises(TomlError) as exc_info:
        load_toml(toml_file)

    # Verify the error message contains information about the parsing error
    assert "invalid.toml" in str(exc_info.value)
    assert "Error loading TOML file" in str(exc_info.value)


def test_load_toml_empty_file(tmp_path: Path) -> None:
    """Test loading an empty TOML file returns empty dict."""
    # Create an empty TOML file
    toml_file = tmp_path / "empty.toml"
    toml_file.write_text("")

    # Load the empty file
    result = load_toml(toml_file)

    # Assert an empty dict is returned
    assert isinstance(result, dict)
    assert len(result) == 0


def test_load_toml_nested_structure(tmp_path: Path) -> None:
    """Test loading TOML with nested structure."""
    # Create a TOML file with nested tables
    toml_file = tmp_path / "nested.toml"
    toml_content = """
[section1]
key1 = "value1"

[section1.subsection]
key2 = "value2"

[[section2.array]]
name = "item1"

[[section2.array]]
name = "item2"
"""
    toml_file.write_text(toml_content)

    # Load the TOML file
    result = load_toml(toml_file)

    # Assert the nested structure is correct
    assert isinstance(result, dict)
    assert result["section1"]["key1"] == "value1"
    assert result["section1"]["subsection"]["key2"] == "value2"
    assert len(result["section2"]["array"]) == 2
    assert result["section2"]["array"][0]["name"] == "item1"
    assert result["section2"]["array"][1]["name"] == "item2"


def test_toml_error_exception() -> None:
    """Test that TomlError exception works correctly."""
    error_message = "Test error message"
    error = TomlError(error_message)

    # Check the message is formatted correctly
    assert str(error) == f"TomlError: {error_message}"
    assert error.message == error_message


def test_load_toml_path_object(tmp_path: Path) -> None:
    """Test that load_toml works with Path object directly."""
    # Create a valid TOML file
    toml_file = tmp_path / "path_test.toml"
    toml_content = """
[config]
enabled = true
"""
    toml_file.write_text(toml_content)

    # Load using Path object
    result = load_toml(toml_file)

    # Assert it loaded correctly
    assert isinstance(result, dict)
    assert result["config"]["enabled"] is True
