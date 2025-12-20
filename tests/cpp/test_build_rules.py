"""Tests for C++ rule building functionality."""

from __future__ import annotations

import typing

import pytest

from devops.config.config_cpp import CppConfig
from devops.cpp.build_rules import build_cpp_rules
from devops.rules import Rule, RuleType

if typing.TYPE_CHECKING:
    from pathlib import Path


class TestBuildCppRules:
    """Tests for build_cpp_rules function."""

    def setup_method(self) -> None:
        """Reset rule counters before each test."""
        Rule.cpp_style_rule_counter = 0
        Rule.general_rule_counter = 0

    def test_build_cpp_rules_with_defaults(self) -> None:
        """Test building rules with default configuration."""
        config = CppConfig()
        rules = build_cpp_rules(config)

        # Default config has style_checks=True, license_header_check=True
        # but license_header=None, so only style rules should be included
        assert isinstance(rules, list)
        # Should contain style rules but no license header rule
        assert len(rules) > 0
        assert all(isinstance(rule, Rule) for rule in rules)
        # All should be style rules
        assert all(rule.rule_type == RuleType.CPP_STYLE for rule in rules)

    def test_build_cpp_rules_with_style_checks_disabled(self) -> None:
        """Test building rules with style checks disabled."""
        config = CppConfig(style_checks=False, license_header_check=False)
        rules = build_cpp_rules(config)

        # With both checks disabled, should return empty list
        assert rules == []

    def test_build_cpp_rules_with_only_style_checks(self) -> None:
        """Test building rules with only style checks enabled."""
        config = CppConfig(style_checks=True, license_header_check=False)
        rules = build_cpp_rules(config)

        # Should contain only style rules
        assert len(rules) > 0
        assert all(rule.rule_type == RuleType.CPP_STYLE for rule in rules)
        # None should be license header checks
        assert all(rule.name != "License Header Check" for rule in rules)

    def test_build_cpp_rules_with_license_header_check_enabled(
        self, tmp_path: Path
    ) -> None:
        """Test building rules with license header check enabled.

        Parameters
        ----------
        tmp_path: Path
            Temporary path for creating test files.

        """
        # Create a license header file
        header_file = tmp_path / "header.txt"
        header_file.write_text("// Copyright 2024\n")

        config = CppConfig(
            style_checks=True,
            license_header_check=True,
            license_header=str(header_file),
        )
        rules = build_cpp_rules(config)

        # Should contain style rules + license header rule
        assert len(rules) > 0
        # Check that license header rule is present
        license_rules = [rule for rule in rules if rule.name == "License Header Check"]
        assert len(license_rules) == 1

    def test_build_cpp_rules_license_header_without_path(self, caplog) -> None:
        """Test building rules with license header check but no path.

        Parameters
        ----------
        caplog
            Pytest fixture for capturing log messages.

        """
        config = CppConfig(
            style_checks=False,
            license_header_check=True,
            license_header=None,  # No header file provided
        )
        rules = build_cpp_rules(config)

        # Should not contain license header rule
        assert rules == []
        # Should log a warning
        assert any("License header check is enabled" in record.message for record in caplog.records)
        assert any("no license header text is provided" in record.message for record in caplog.records)

    def test_build_cpp_rules_with_only_license_header(self, tmp_path: Path) -> None:
        """Test building rules with only license header check.

        Parameters
        ----------
        tmp_path: Path
            Temporary path for creating test files.

        """
        # Create a license header file
        header_file = tmp_path / "header.txt"
        header_file.write_text("// Header\n")

        config = CppConfig(
            style_checks=False,
            license_header_check=True,
            license_header=str(header_file),
        )
        rules = build_cpp_rules(config)

        # Should contain only the license header rule
        assert len(rules) == 1
        assert rules[0].name == "License Header Check"

    def test_build_cpp_rules_all_checks_enabled(self, tmp_path: Path) -> None:
        """Test building rules with all checks enabled.

        Parameters
        ----------
        tmp_path: Path
            Temporary path for creating test files.

        """
        # Create a license header file
        header_file = tmp_path / "header.txt"
        header_file.write_text("// Header\n")

        config = CppConfig(
            style_checks=True,
            license_header_check=True,
            license_header=str(header_file),
        )
        rules = build_cpp_rules(config)

        # Should contain both style rules and license header rule
        assert len(rules) > 1
        license_rules = [rule for rule in rules if rule.name == "License Header Check"]
        assert len(license_rules) == 1

    def test_build_cpp_rules_check_only_staged_files_has_no_effect(
        self, tmp_path: Path
    ) -> None:
        """Test that check_only_staged_files doesn't affect rule building.

        Parameters
        ----------
        tmp_path: Path
            Temporary path for creating test files.

        """
        header_file = tmp_path / "header.txt"
        header_file.write_text("// Header\n")

        config1 = CppConfig(
            style_checks=True,
            license_header_check=True,
            license_header=str(header_file),
            check_only_staged_files=False,
        )
        config2 = CppConfig(
            style_checks=True,
            license_header_check=True,
            license_header=str(header_file),
            check_only_staged_files=True,
        )

        rules1 = build_cpp_rules(config1)
        rules2 = build_cpp_rules(config2)

        # Should produce the same rules regardless of check_only_staged_files
        assert len(rules1) == len(rules2)

    def test_build_cpp_rules_returns_list_of_rules(self) -> None:
        """Test that build_cpp_rules returns a list of Rule objects."""
        config = CppConfig(style_checks=True, license_header_check=False)
        rules = build_cpp_rules(config)

        assert isinstance(rules, list)
        assert all(isinstance(rule, Rule) for rule in rules)

    def test_build_cpp_rules_style_rules_are_cpp_type(self) -> None:
        """Test that all style rules have CPP_STYLE type."""
        config = CppConfig(style_checks=True, license_header_check=False)
        rules = build_cpp_rules(config)

        # All returned rules should be CPP_STYLE type
        assert all(rule.rule_type == RuleType.CPP_STYLE for rule in rules)
