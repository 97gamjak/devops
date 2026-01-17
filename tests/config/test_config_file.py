"""Tests for devops.config.config_file module."""

from pathlib import Path

import pytest

from devops.config.base import ConfigError
from devops.config.config_file import parse_changelog_path


def test_parse_changelog_path_with_single_string() -> None:
    """Test parsing a single string path."""
    table = {"changelog_paths": "CHANGELOG.md"}
    result = parse_changelog_path(table)

    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0] == Path("CHANGELOG.md")


def test_parse_changelog_path_with_list_of_paths() -> None:
    """Test parsing a list of paths."""
    table = {"changelog_paths": ["CHANGELOG.md", "docs/HISTORY.md", "RELEASES.md"]}
    result = parse_changelog_path(table)

    assert isinstance(result, list)
    assert len(result) == 3
    assert result[0] == Path("CHANGELOG.md")
    assert result[1] == Path("docs/HISTORY.md")
    assert result[2] == Path("RELEASES.md")


def test_parse_changelog_path_with_missing_key() -> None:
    """Test parsing with missing key returns default."""
    table: dict[str, str | list[str]] = {}
    result = parse_changelog_path(table)

    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0] == Path("CHANGELOG.md")


def test_parse_changelog_path_with_none_value() -> None:
    """Test parsing with None value returns default."""
    table = {"changelog_paths": None}
    result = parse_changelog_path(table)

    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0] == Path("CHANGELOG.md")


def test_parse_changelog_path_with_invalid_type_int() -> None:
    """Test parsing with invalid type (int) raises ConfigError."""
    table = {"changelog_paths": 42}

    with pytest.raises(ConfigError) as exc_info:
        parse_changelog_path(table)

    assert "Expected str or list of str for key 'changelog_paths'" in str(exc_info.value)
    assert "got int" in str(exc_info.value)


def test_parse_changelog_path_with_invalid_type_dict() -> None:
    """Test parsing with invalid type (dict) raises ConfigError."""
    table = {"changelog_paths": {"path": "CHANGELOG.md"}}

    with pytest.raises(ConfigError) as exc_info:
        parse_changelog_path(table)

    assert "Expected str or list of str for key 'changelog_paths'" in str(exc_info.value)
    assert "got dict" in str(exc_info.value)


def test_parse_changelog_path_with_list_containing_non_strings() -> None:
    """Test parsing with list containing non-string elements raises ConfigError."""
    table = {"changelog_paths": ["CHANGELOG.md", 42, "RELEASES.md"]}

    with pytest.raises(ConfigError) as exc_info:
        parse_changelog_path(table)

    assert "Expected str or list of str for key 'changelog_paths'" in str(exc_info.value)
    assert "got list with non-string items" in str(exc_info.value)


def test_parse_changelog_path_with_empty_list() -> None:
    """Test parsing with empty list returns empty list."""
    table = {"changelog_paths": []}
    result = parse_changelog_path(table)

    assert isinstance(result, list)
    assert len(result) == 0
