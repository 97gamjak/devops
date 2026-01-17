"""Tests for devops.config.config_file module."""

from pathlib import Path

import pytest

from devops.config.base import ConfigError
from devops.config.config_file import parse_changelog_path


def test_parse_changelog_path_single_string() -> None:
    """Test parsing a single string path."""
    table = {"changelog_paths": "CHANGELOG.md"}
    result = parse_changelog_path(table)

    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0] == Path("CHANGELOG.md")
    assert isinstance(result[0], Path)


def test_parse_changelog_path_list_of_paths() -> None:
    """Test parsing a list of paths."""
    table = {"changelog_paths": ["CHANGELOG.md", "HISTORY.md", "docs/CHANGELOG.md"]}
    result = parse_changelog_path(table)

    assert isinstance(result, list)
    assert len(result) == 3
    assert result[0] == Path("CHANGELOG.md")
    assert result[1] == Path("HISTORY.md")
    assert result[2] == Path("docs/CHANGELOG.md")
    assert all(isinstance(p, Path) for p in result)


def test_parse_changelog_path_missing_key_uses_default() -> None:
    """Test that missing key uses default value."""
    table: dict[str, str] = {}
    result = parse_changelog_path(table)

    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0] == Path("CHANGELOG.md")
    assert isinstance(result[0], Path)


def test_parse_changelog_path_invalid_type_integer() -> None:
    """Test that invalid input type (integer) raises ConfigError."""
    table = {"changelog_paths": 123}

    with pytest.raises(ConfigError) as exc_info:
        parse_changelog_path(table)

    assert "Expected str or list of str for key 'changelog_paths'" in str(exc_info.value)
    assert "got int" in str(exc_info.value)


def test_parse_changelog_path_invalid_type_dict() -> None:
    """Test that invalid input type (dict) raises ConfigError."""
    table = {"changelog_paths": {"path": "CHANGELOG.md"}}

    with pytest.raises(ConfigError) as exc_info:
        parse_changelog_path(table)

    assert "Expected str or list of str for key 'changelog_paths'" in str(exc_info.value)
    assert "got dict" in str(exc_info.value)


def test_parse_changelog_path_invalid_type_list_with_non_strings() -> None:
    """Test that list with non-string elements raises ConfigError."""
    table = {"changelog_paths": ["CHANGELOG.md", 123, "HISTORY.md"]}

    with pytest.raises(ConfigError) as exc_info:
        parse_changelog_path(table)

    assert "Expected str or list of str for key 'changelog_paths'" in str(exc_info.value)
    assert "list with non-string items" in str(exc_info.value)


def test_parse_changelog_path_empty_list() -> None:
    """Test parsing an empty list returns empty list."""
    table = {"changelog_paths": []}
    result = parse_changelog_path(table)

    assert isinstance(result, list)
    assert len(result) == 0


def test_parse_changelog_path_single_item_list() -> None:
    """Test parsing a single-item list."""
    table = {"changelog_paths": ["HISTORY.md"]}
    result = parse_changelog_path(table)

    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0] == Path("HISTORY.md")


def test_parse_changelog_path_paths_with_subdirectories() -> None:
    """Test parsing paths with subdirectories."""
    table = {"changelog_paths": ["docs/v1/CHANGELOG.md", "docs/v2/CHANGELOG.md"]}
    result = parse_changelog_path(table)

    assert isinstance(result, list)
    assert len(result) == 2
    assert result[0] == Path("docs/v1/CHANGELOG.md")
    assert result[1] == Path("docs/v2/CHANGELOG.md")
