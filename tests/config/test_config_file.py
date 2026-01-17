"""Tests for devops.config.config_file module."""

from pathlib import Path

import pytest

from devops.config.base import ConfigError
from devops.config.config_file import (
    FileConfig,
    parse_default_changelog_path,
    parse_file_config,
)


class TestParseDefaultChangelogPath:
    """Tests for parse_default_changelog_path function."""

    def test_parse_default_changelog_path_with_valid_path(self) -> None:
        """Test parsing a valid path string."""
        table = {"default_changelog_path": "docs/CHANGELOG.md"}
        result = parse_default_changelog_path(table)

        assert result == Path("docs/CHANGELOG.md")
        assert isinstance(result, Path)

    def test_parse_default_changelog_path_with_none(self) -> None:
        """Test parsing when key is missing returns None."""
        table: dict[str, str] = {}
        result = parse_default_changelog_path(table)

        assert result is None

    def test_parse_default_changelog_path_with_explicit_none(self) -> None:
        """Test parsing when value is explicitly None."""
        table = {"default_changelog_path": None}
        result = parse_default_changelog_path(table)

        assert result is None

    def test_parse_default_changelog_path_with_relative_path(self) -> None:
        """Test parsing with a relative path."""
        table = {"default_changelog_path": "../CHANGES.md"}
        result = parse_default_changelog_path(table)

        assert result == Path("../CHANGES.md")

    def test_parse_default_changelog_path_with_absolute_path(self) -> None:
        """Test parsing with an absolute path."""
        table = {"default_changelog_path": "/usr/local/CHANGELOG.md"}
        result = parse_default_changelog_path(table)

        assert result == Path("/usr/local/CHANGELOG.md")


class TestFileConfigDefaultChangelogPathInteraction:
    """Tests for how default_changelog_path interacts with FileConfig."""

    def test_file_config_uses_explicit_default_changelog_path(self) -> None:
        """Test that FileConfig uses explicit default_changelog_path when provided."""
        raw_config = {
            "file": {
                "changelog_paths": ["CHANGELOG.md", "docs/CHANGELOG.md"],
                "default_changelog_path": "docs/CHANGELOG.md",
            }
        }
        result = parse_file_config(raw_config)

        assert result.default_changelog_path == Path("docs/CHANGELOG.md")
        assert result.changelog_paths == [
            Path("CHANGELOG.md"),
            Path("docs/CHANGELOG.md"),
        ]

    def test_file_config_defaults_to_first_changelog_path(self) -> None:
        """Test FileConfig defaults to first changelog_path when no default present."""
        raw_config = {
            "file": {
                "changelog_paths": ["CHANGELOG.md", "docs/CHANGELOG.md"],
            }
        }
        result = parse_file_config(raw_config)

        assert result.default_changelog_path == Path("CHANGELOG.md")

    def test_file_config_default_changelog_path_with_single_path(self) -> None:
        """Test default_changelog_path with single changelog path."""
        raw_config = {
            "file": {
                "changelog_paths": "CHANGELOG.md",
            }
        }
        result = parse_file_config(raw_config)

        assert result.default_changelog_path == Path("CHANGELOG.md")

    def test_file_config_default_changelog_path_not_in_list(self) -> None:
        """Test that default_changelog_path can be different from changelog_paths."""
        raw_config = {
            "file": {
                "changelog_paths": ["CHANGELOG.md"],
                "default_changelog_path": "docs/CHANGES.md",
            }
        }
        result = parse_file_config(raw_config)

        # The default_changelog_path doesn't need to be in changelog_paths
        assert result.default_changelog_path == Path("docs/CHANGES.md")
        assert result.changelog_paths == [Path("CHANGELOG.md")]

    def test_file_config_raises_error_when_no_paths_configured(self) -> None:
        """Test accessing default_changelog_path.

        When no changelog paths are configured, accessing default_changelog_path
        """
        # Create a FileConfig with empty changelog_paths and no default
        config = FileConfig(changelog_paths=[], _default_changelog_path=None)

        with pytest.raises(ConfigError) as exc_info:
            _ = config.default_changelog_path

        assert "No changelog paths configured" in str(exc_info.value)
        assert "cannot determine default changelog path" in str(exc_info.value)

    def test_file_config_with_no_file_section(self) -> None:
        """Test parsing config with no file section uses defaults."""
        raw_config: dict[str, dict[str, str]] = {}
        result = parse_file_config(raw_config)

        # Should use defaults
        assert result.default_changelog_path == Path("CHANGELOG.md")
        assert result.changelog_paths == [Path("CHANGELOG.md")]
