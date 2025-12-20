"""Unit tests for cpp_checks script module."""

from __future__ import annotations

import typing
from unittest.mock import patch

from devops.cpp import build_cpp_rules, run_cpp_checks
from devops.cpp.checks import run_line_checks
from devops.files import FileType
from devops.rules import ResultType, ResultTypeEnum, Rule, RuleInputType, RuleType
from devops.scripts.cpp_checks import app

if typing.TYPE_CHECKING:
    from pathlib import Path

cpp_rules = build_cpp_rules()


class TestRunLineChecks:
    """Tests for run_line_checks function."""

    def setup_method(self) -> None:
        """Reset rule counters before each test."""
        Rule.cpp_style_rule_counter = 0
        Rule.general_rule_counter = 0

    def test_run_line_checks_with_matching_rule(self, tmp_path: Path) -> None:
        """Test run_line_checks applies rule to matching file type.

        Parameters
        ----------
        tmp_path: Path
            Temporary path for creating test files.

        """
        test_file = tmp_path / "test.cpp"
        test_file.write_text("static inline constexpr int x = 42;\n")

        rule = Rule(
            name="test_rule",
            func=lambda _line: ResultType(ResultTypeEnum.Ok),
            rule_type=RuleType.CPP_STYLE,
            rule_input_type=RuleInputType.LINE,
        )

        results = run_line_checks([rule], test_file)
        assert len(results) == 1
        assert results[0].value == ResultTypeEnum.Ok

    def test_run_line_checks_with_non_matching_file_type(self, tmp_path: Path) -> None:
        """Test run_line_checks skips rule when file type doesn't match.

        Parameters
        ----------
        tmp_path: Path
            Temporary path for creating test files.

        """
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content\n")

        rule = Rule(
            name="cpp_only_rule",
            func=lambda _line: ResultType(ResultTypeEnum.Error, "Should not run"),
            rule_type=RuleType.CPP_STYLE,
            rule_input_type=RuleInputType.LINE,
            file_types={FileType.CPPSource},
        )

        results = run_line_checks([rule], test_file)
        assert len(results) == 0

    def test_run_line_checks_multiple_lines(self, tmp_path: Path) -> None:
        """Test run_line_checks processes all lines.

        Parameters
        ----------
        tmp_path: Path
            Temporary path for creating test files.

        """
        test_file = tmp_path / "test.cpp"
        test_file.write_text("line1\nline2\nline3\n")

        rule = Rule(
            name="count_rule",
            func=lambda _line: ResultType(ResultTypeEnum.Ok),
            rule_type=RuleType.CPP_STYLE,
            rule_input_type=RuleInputType.LINE,
        )

        results = run_line_checks([rule], test_file)
        assert len(results) == 3

    def test_run_line_checks_multiple_rules(self, tmp_path: Path) -> None:
        """Test run_line_checks applies multiple rules.

        Parameters
        ----------
        tmp_path: Path
            Temporary path for creating test files.

        """
        test_file = tmp_path / "test.cpp"
        test_file.write_text("test line\n")

        rule1 = Rule(
            name="rule1",
            func=lambda _line: ResultType(ResultTypeEnum.Ok),
            rule_type=RuleType.CPP_STYLE,
            rule_input_type=RuleInputType.LINE,
        )
        rule2 = Rule(
            name="rule2",
            func=lambda _line: ResultType(ResultTypeEnum.Ok),
            rule_type=RuleType.CPP_STYLE,
            rule_input_type=RuleInputType.LINE,
        )

        results = run_line_checks([rule1, rule2], test_file)
        assert len(results) == 2

    def test_run_line_checks_filters_non_line_rules(self, tmp_path: Path) -> None:
        """Test run_line_checks only applies LINE input type rules.

        Parameters
        ----------
        tmp_path: Path
            Temporary path for creating test files.

        """
        test_file = tmp_path / "test.cpp"
        test_file.write_text("test line\n")

        line_rule = Rule(
            name="line_rule",
            func=lambda _line: ResultType(ResultTypeEnum.Ok),
            rule_type=RuleType.CPP_STYLE,
            rule_input_type=RuleInputType.LINE,
        )
        file_rule = Rule(
            name="file_rule",
            func=lambda _line: ResultType(ResultTypeEnum.Error, "Should not run"),
            rule_type=RuleType.CPP_STYLE,
            rule_input_type=RuleInputType.FILE,
        )

        results = run_line_checks([line_rule, file_rule], test_file)
        assert len(results) == 1
        assert results[0].value == ResultTypeEnum.Ok

    def test_run_line_checks_empty_file(self, tmp_path: Path) -> None:
        """Test run_line_checks handles empty files.

        Parameters
        ----------
        tmp_path: Path
            Temporary path for creating test files.

        """
        test_file = tmp_path / "empty.cpp"
        test_file.write_text("")

        rule = Rule(
            name="test_rule",
            func=lambda _line: ResultType(ResultTypeEnum.Ok),
            rule_type=RuleType.CPP_STYLE,
            rule_input_type=RuleInputType.LINE,
        )

        results = run_line_checks([rule], test_file)
        assert len(results) == 0

    def test_run_line_checks_no_rules(self, tmp_path: Path) -> None:
        """Test run_line_checks with no rules.

        Parameters
        ----------
        tmp_path: Path
            Temporary path for creating test files.

        """
        test_file = tmp_path / "test.cpp"
        test_file.write_text("test content\n")

        results = run_line_checks([], test_file)
        assert len(results) == 0
