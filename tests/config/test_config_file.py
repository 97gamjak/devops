"""Tests for devops.config.config_file module."""

from pathlib import Path

import pytest

from devops.config.base import ConfigError
from devops.config.config_file import (
    FileConfig,
    parse_default_changelog_path,
    parse_file_config,
)


def test_parse_default_changelog_path_with_valid_string() -> None:
    """Test parse_default_changelog_path with a valid path string."""
    table = {"default_changelog_path": "CHANGELOG-custom.md"}

    result = parse_default_changelog_path(table)

    assert result == Path("CHANGELOG-custom.md")
    assert isinstance(result, Path)


def test_parse_default_changelog_path_with_none_value() -> None:
    """Test parse_default_changelog_path when key has None value."""
    table = {"default_changelog_path": None}

    result = parse_default_changelog_path(table)

    assert result is None


def test_parse_default_changelog_path_with_missing_key() -> None:
    """Test parse_default_changelog_path when key is missing from table."""
    table: dict[str, str] = {}

    result = parse_default_changelog_path(table)

    assert result is None


def test_parse_default_changelog_path_with_different_paths() -> None:
    """Test parse_default_changelog_path with various path formats."""
    test_cases = [
        "CHANGELOG.md",
        "docs/CHANGELOG.md",
        "path/to/CHANGELOG.txt",
        "HISTORY.md",
    ]

    for path_str in test_cases:
        table = {"default_changelog_path": path_str}
        result = parse_default_changelog_path(table)
        assert result == Path(path_str)
        assert isinstance(result, Path)


def test_parse_default_changelog_path_with_absolute_path() -> None:
    """Test parse_default_changelog_path with an absolute path."""
    table = {"default_changelog_path": "/absolute/path/to/CHANGELOG.md"}

    result = parse_default_changelog_path(table)

    assert result == Path("/absolute/path/to/CHANGELOG.md")


def test_file_config_uses_default_changelog_path() -> None:
    """Test FileConfig uses _default_changelog_path when set."""
    raw_config = {
        "file": {
            "changelog_paths": ["CHANGELOG1.md", "CHANGELOG2.md"],
            "default_changelog_path": "CHANGELOG2.md",
        }
    }

    config = parse_file_config(raw_config)

    assert config.default_changelog_path == Path("CHANGELOG2.md")
    assert config.changelog_paths == [Path("CHANGELOG1.md"), Path("CHANGELOG2.md")]


def test_file_config_default_path_fallback_to_first_changelog() -> None:
    """Test FileConfig falls back to first changelog_path when no default set."""
    raw_config = {
        "file": {
            "changelog_paths": ["FIRST.md", "SECOND.md"],
        }
    }

    config = parse_file_config(raw_config)

    # Should fall back to first path in changelog_paths
    assert config.default_changelog_path == Path("FIRST.md")


def test_file_config_default_path_independent_of_changelog_paths() -> None:
    """Test default_changelog_path can be set independently of changelog_paths."""
    raw_config = {
        "file": {
            "changelog_paths": ["CHANGELOG1.md", "CHANGELOG2.md"],
            "default_changelog_path": "CUSTOM.md",
        }
    }

    config = parse_file_config(raw_config)

    # default_changelog_path can be different from any in changelog_paths
    assert config.default_changelog_path == Path("CUSTOM.md")
    assert Path("CUSTOM.md") not in config.changelog_paths


def test_file_config_no_changelog_paths_and_no_default_raises_error() -> None:
    """Test FileConfig raises error when no changelog paths configured and default accessed."""
    # This scenario shouldn't happen in normal usage since parse_file_config
    # provides defaults, but we test the property behavior directly
    config = FileConfig(changelog_paths=[], _default_changelog_path=None)

    with pytest.raises(ConfigError) as exc_info:
        _ = config.default_changelog_path

    assert "No changelog paths configured" in str(exc_info.value)


def test_file_config_with_only_default_path_set() -> None:
    """Test FileConfig when only default_changelog_path is explicitly set."""
    raw_config = {
        "file": {
            "default_changelog_path": "SPECIFIC.md",
        }
    }

    config = parse_file_config(raw_config)

    # changelog_paths should use the default
    assert config.changelog_paths == [Path("CHANGELOG.md")]
    # default_changelog_path should be the explicitly set one
    assert config.default_changelog_path == Path("SPECIFIC.md")
