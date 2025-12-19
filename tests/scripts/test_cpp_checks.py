"""Unit tests for cpp_checks script module."""

from __future__ import annotations

import typing
from unittest.mock import patch

from devops.cpp import cpp_rules
from devops.files import FileType
from devops.rules import ResultType, ResultTypeEnum, Rule, RuleInputType, RuleType
from devops.scripts.cpp_checks import main, run_checks, run_line_checks

if typing.TYPE_CHECKING:
    from pathlib import Path


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


class TestRunChecks:
    """Tests for run_checks function."""

    def setup_method(self) -> None:
        """Reset rule counters before each test."""
        Rule.cpp_style_rule_counter = 0
        Rule.general_rule_counter = 0

    @patch("devops.scripts.cpp_checks.get_staged_files")
    @patch("devops.scripts.cpp_checks.cpp_check_logger")
    def test_run_checks_no_files(self, mock_logger: any, mock_get_staged: any) -> None:
        """Test run_checks logs warning when no files to check.

        Parameters
        ----------
        mock_logger: any
            Mocked logger.
        mock_get_staged: any
            Mocked function to get staged files.

        """
        mock_get_staged.return_value = []

        rules = [
            Rule(
                name="test_rule",
                func=lambda _line: ResultType(ResultTypeEnum.Ok),
                rule_input_type=RuleInputType.LINE,
            )
        ]

        run_checks(rules)

        mock_logger.warning.assert_called_once_with("No files to check.")

    @patch("devops.scripts.cpp_checks.get_staged_files")
    @patch("devops.scripts.cpp_checks.cpp_check_logger")
    def test_run_checks_staged_mode(
        self, mock_logger: any, mock_get_staged: any, tmp_path: Path
    ) -> None:
        """Test run_checks in staged files mode.

        Parameters
        ----------
        mock_logger: any
            Mocked logger.
        mock_get_staged: any
            Mocked function to get staged files.
        tmp_path: Path
            Temporary path for creating test files.

        """
        test_file = tmp_path / "test.cpp"
        test_file.write_text("test content\n")
        mock_get_staged.return_value = [test_file]

        rule = Rule(
            name="test_rule",
            func=lambda _line: ResultType(ResultTypeEnum.Ok),
            rule_type=RuleType.CPP_STYLE,
            rule_input_type=RuleInputType.LINE,
        )

        with (
            patch.object(Rule, "cpp_style_rule_counter", 0),
            patch.object(Rule, "general_rule_counter", 0),
        ):
            run_checks([rule])

        mock_logger.info.assert_called_with("Running checks on staged files...")

    @patch("devops.scripts.cpp_checks.get_files_in_dirs")
    @patch("devops.scripts.cpp_checks.cpp_check_logger")
    @patch("sys.argv", ["cpp_checks", "full"])
    def test_run_checks_full_mode(
        self, mock_logger: any, mock_get_files: any, tmp_path: Path
    ) -> None:
        """Test run_checks in full mode.

        Parameters
        ----------
        mock_logger: any
            Mocked logger.
        mock_get_files: any
            Mocked function to get all files in directories.
        tmp_path: Path
            Temporary path for creating test files.

        """
        test_file = tmp_path / "test.cpp"
        test_file.write_text("test content\n")
        mock_get_files.return_value = [test_file]

        rule = Rule(
            name="test_rule",
            func=lambda _line: ResultType(ResultTypeEnum.Ok),
            rule_type=RuleType.CPP_STYLE,
            rule_input_type=RuleInputType.LINE,
        )

        with (
            patch.object(Rule, "cpp_style_rule_counter", 0),
            patch.object(Rule, "general_rule_counter", 0),
        ):
            run_checks([rule])

        mock_logger.info.assert_called_with("Running full checks...")

    @patch("devops.scripts.cpp_checks.get_staged_files")
    @patch("devops.scripts.cpp_checks.cpp_check_logger")
    def test_run_checks_with_errors(
        self, mock_logger: any, mock_get_staged: any, tmp_path: Path
    ) -> None:
        """Test run_checks logs errors when rule fails.

        Parameters
        ----------
        mock_logger: any
            Mocked logger.
        mock_get_staged: any
            Mocked function to get staged files.
        tmp_path: Path
            Temporary path for creating test files.

        """
        test_file = tmp_path / "test.cpp"
        test_file.write_text("bad code\n")
        mock_get_staged.return_value = [test_file]

        rule = Rule(
            name="failing_rule",
            func=lambda _line: ResultType(ResultTypeEnum.Error, "Error found"),
            rule_type=RuleType.CPP_STYLE,
            rule_input_type=RuleInputType.LINE,
        )

        with (
            patch.object(Rule, "cpp_style_rule_counter", 0),
            patch.object(Rule, "general_rule_counter", 0),
        ):
            run_checks([rule])

        assert mock_logger.error.called

    @patch("devops.scripts.cpp_checks.get_staged_files")
    @patch("devops.scripts.cpp_checks.cpp_check_logger")
    def test_run_checks_stops_on_first_file_with_errors(
        self, mock_logger: any, mock_get_staged: any, tmp_path: Path
    ) -> None:
        """Test run_checks returns after first file with errors.

        Parameters
        ----------
        mock_logger: any
            Mocked logger.
        mock_get_staged: any
            Mocked function to get staged files.
        tmp_path: Path
            Temporary path for creating test files.

        """
        file1 = tmp_path / "test1.cpp"
        file1.write_text("bad code\n")
        file2 = tmp_path / "test2.cpp"
        file2.write_text("more code\n")
        mock_get_staged.return_value = [file1, file2]

        call_count = [0]

        def counting_func(_line: str) -> ResultType:
            call_count[0] += 1
            return ResultType(ResultTypeEnum.Error, "Error")

        rule = Rule(
            name="counting_rule",
            func=counting_func,
            rule_type=RuleType.CPP_STYLE,
            rule_input_type=RuleInputType.LINE,
        )

        with (
            patch.object(Rule, "cpp_style_rule_counter", 0),
            patch.object(Rule, "general_rule_counter", 0),
        ):
            run_checks([rule])

        # Should stop after first file
        assert call_count[0] == 1
        assert mock_logger.error.called


class TestMain:
    """Tests for main function."""

    def setup_method(self) -> None:
        """Reset rule counters before each test."""
        Rule.cpp_style_rule_counter = 0
        Rule.general_rule_counter = 0

    @patch("devops.scripts.cpp_checks.run_checks")
    def test_main_calls_run_checks(self, mock_run_checks: any) -> None:
        """Test main function calls run_checks with cpp_rules.

        Parameters
        ----------
        mock_run_checks: any
            Mocked run_checks function.

        """
        main()

        mock_run_checks.assert_called_once_with(cpp_rules)

    @patch("devops.scripts.cpp_checks.get_staged_files")
    @patch("devops.scripts.cpp_checks.cpp_check_logger")
    def test_main_integration(
        self, mock_logger: any, mock_get_staged: any, tmp_path: Path
    ) -> None:
        """Test main function integration."""
        test_file = tmp_path / "test.cpp"
        test_file.write_text("static inline constexpr int x = 42;\n")
        mock_get_staged.return_value = [test_file]

        main()

        mock_logger.info.assert_called()
