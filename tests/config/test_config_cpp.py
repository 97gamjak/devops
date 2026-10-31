"""Tests for C++ configuration parsing."""

import pytest

from devops.config.base import ConfigError
from devops.config.config_cpp import CppConfig, parse_cpp_config


class TestCppConfigDefaults:
    """Tests for CppConfig default values."""

    def test_cpp_config_default_values(self) -> None:
        """Test CppConfig has correct default values."""
        config = CppConfig()
        assert config.style_checks is True
        assert config.license_header_check is True
        assert config.license_header is None
        assert config.check_only_staged_files is False


class TestParseCppConfig:
    """Tests for parse_cpp_config function."""

    def test_parse_cpp_config_with_all_values(self) -> None:
        """Test parsing C++ config with all values specified."""
        raw_config = {
            "cpp": {
                "style_checks": False,
                "license_header_check": True,
                "license_header": "/path/to/header.txt",
                "check_only_staged_files": True,
            }
        }
        config = parse_cpp_config(raw_config)

        assert isinstance(config, CppConfig)
        assert config.style_checks is False
        assert config.license_header_check is True
        assert config.license_header == "/path/to/header.txt"
        assert config.check_only_staged_files is True

    def test_parse_cpp_config_with_defaults(self) -> None:
        """Test parsing C++ config with missing keys uses defaults."""
        raw_config = {"cpp": {}}
        config = parse_cpp_config(raw_config)

        assert isinstance(config, CppConfig)
        assert config.style_checks is True
        assert config.license_header_check is True
        assert config.license_header is None
        assert config.check_only_staged_files is False

    def test_parse_cpp_config_missing_cpp_section(self) -> None:
        """Test parsing config without 'cpp' section returns defaults."""
        raw_config: dict = {}
        config = parse_cpp_config(raw_config)

        assert isinstance(config, CppConfig)
        assert config.style_checks is True
        assert config.license_header_check is True
        assert config.license_header is None
        assert config.check_only_staged_files is False

    def test_parse_cpp_config_partial_values(self) -> None:
        """Test parsing C++ config with some values specified."""
        raw_config = {
            "cpp": {
                "style_checks": False,
                "license_header": "/path/to/license.txt",
            }
        }
        config = parse_cpp_config(raw_config)

        assert config.style_checks is False
        assert config.license_header_check is True  # default
        assert config.license_header == "/path/to/license.txt"
        assert config.check_only_staged_files is False  # default

    def test_parse_cpp_config_style_checks_false(self) -> None:
        """Test parsing C++ config with style_checks disabled."""
        raw_config = {"cpp": {"style_checks": False}}
        config = parse_cpp_config(raw_config)

        assert config.style_checks is False

    def test_parse_cpp_config_license_header_check_false(self) -> None:
        """Test parsing C++ config with license_header_check disabled."""
        raw_config = {"cpp": {"license_header_check": False}}
        config = parse_cpp_config(raw_config)

        assert config.license_header_check is False

    def test_parse_cpp_config_check_only_staged_files_true(self) -> None:
        """Test parsing C++ config with check_only_staged_files enabled."""
        raw_config = {"cpp": {"check_only_staged_files": True}}
        config = parse_cpp_config(raw_config)

        assert config.check_only_staged_files is True

    def test_parse_cpp_config_none_license_header(self) -> None:
        """Test parsing C++ config with explicit None for license_header."""
        raw_config = {"cpp": {"license_header": None}}
        config = parse_cpp_config(raw_config)

        assert config.license_header is None

    def test_parse_cpp_config_all_booleans_true(self) -> None:
        """Test parsing C++ config with all boolean values as True."""
        raw_config = {
            "cpp": {
                "style_checks": True,
                "license_header_check": True,
                "check_only_staged_files": True,
            }
        }
        config = parse_cpp_config(raw_config)

        assert config.style_checks is True
        assert config.license_header_check is True
        assert config.check_only_staged_files is True

    def test_parse_cpp_config_all_booleans_false(self) -> None:
        """Test parsing C++ config with all boolean values as False."""
        raw_config = {
            "cpp": {
                "style_checks": False,
                "license_header_check": False,
                "check_only_staged_files": False,
            }
        }
        config = parse_cpp_config(raw_config)

        assert config.style_checks is False
        assert config.license_header_check is False
        assert config.check_only_staged_files is False

    def test_parse_cpp_config_license_header_path(self) -> None:
        """Test parsing C++ config with various license header paths."""
        test_paths = [
            "/absolute/path/to/header.txt",
            "relative/path/to/header.txt",
            "../parent/header.txt",
            "./current/header.txt",
        ]

        for path in test_paths:
            raw_config = {"cpp": {"license_header": path}}
            config = parse_cpp_config(raw_config)
            assert config.license_header == path


class TestHeaderGuardPattern:
    """Tests for the header_guard_pattern config option."""

    def test_default_is_none(self) -> None:
        """Test that header_guard_pattern defaults to None."""
        config = CppConfig()
        assert config.header_guard_pattern is None

    def test_parse_custom_pattern(self) -> None:
        """Test parsing a custom header_guard_pattern."""
        raw_config = {"cpp": {"header_guard_pattern": "{path}_{ext}_GUARD"}}
        config = parse_cpp_config(raw_config)
        assert config.header_guard_pattern == "{path}_{ext}_GUARD"

    def test_parse_missing_pattern_defaults_to_none(self) -> None:
        """Test that an unset header_guard_pattern parses to None."""
        raw_config = {"cpp": {}}
        config = parse_cpp_config(raw_config)
        assert config.header_guard_pattern is None

    def test_parse_empty_string_pattern_defaults_to_none(self) -> None:
        """Test that an empty header_guard_pattern string parses to None."""
        raw_config = {"cpp": {"header_guard_pattern": ""}}
        config = parse_cpp_config(raw_config)
        assert config.header_guard_pattern is None

    def test_parse_pattern_without_path_placeholder_raises(self) -> None:
        """Test that a pattern missing '{path}' raises ConfigError."""
        raw_config = {"cpp": {"header_guard_pattern": "{ext}_GUARD"}}
        with pytest.raises(ConfigError, match="header_guard_pattern"):
            parse_cpp_config(raw_config)
