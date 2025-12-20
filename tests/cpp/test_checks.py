"""Tests for run_cpp_checks function."""

from __future__ import annotations

import logging
import typing
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from devops.config.config_cpp import CppConfig
from devops.cpp.checks import run_cpp_checks
from devops.files import FileType
from devops.rules import ResultType, ResultTypeEnum, Rule, RuleInputType, RuleType

if typing.TYPE_CHECKING:
    from _pytest.logging import LogCaptureFixture


class TestRunCppChecks:
    """Tests for run_cpp_checks function."""

    def setup_method(self) -> None:
        """Reset rule counters before each test."""
        Rule.cpp_style_rule_counter = 0
        Rule.general_rule_counter = 0

    def test_run_cpp_checks_with_no_files(
        self, tmp_path: Path, caplog: LogCaptureFixture
    ) -> None:
        """Test run_cpp_checks when no files are found.

        Parameters
        ----------
        tmp_path: Path
            Temporary path for creating test files.
        caplog
            Pytest fixture for capturing log messages.

        """
        # Create a rule
        rule = Rule(
            name="test_rule",
            func=lambda line: ResultType(ResultTypeEnum.Ok),
            rule_type=RuleType.CPP_STYLE,
            rule_input_type=RuleInputType.LINE,
        )

        # Mock get_staged_files to return empty list
        with patch("devops.cpp.checks.get_staged_files", return_value=[]):
            config = CppConfig(check_only_staged_files=True)
            run_cpp_checks([rule], config)

        # Should log warning about no files
        assert any("No files to check" in record.message for record in caplog.records)

    def test_run_cpp_checks_with_staged_files(self, tmp_path: Path) -> None:
        """Test run_cpp_checks with staged files configuration.

        Parameters
        ----------
        tmp_path: Path
            Temporary path for creating test files.

        """
        # Create test files
        test_file = tmp_path / "test.cpp"
        test_file.write_text("int main() {}\n")

        # Create a passing rule
        rule = Rule(
            name="test_rule",
            func=lambda line: ResultType(ResultTypeEnum.Ok),
            rule_type=RuleType.CPP_STYLE,
            rule_input_type=RuleInputType.LINE,
        )

        # Mock get_staged_files
        with patch("devops.cpp.checks.get_staged_files", return_value=[test_file]):
            config = CppConfig(check_only_staged_files=True)
            run_cpp_checks([rule], config)
            # Should complete without error

    def test_run_cpp_checks_with_full_check(self, tmp_path: Path, monkeypatch) -> None:
        """Test run_cpp_checks with full file check configuration.

        Parameters
        ----------
        tmp_path: Path
            Temporary path for creating test files.
        monkeypatch
            Pytest fixture for monkeypatching.

        """
        # Change to tmp directory
        monkeypatch.chdir(tmp_path)

        # Create test files in subdirectory
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        test_file = src_dir / "test.cpp"
        test_file.write_text("int main() {}\n")

        # Create a passing rule
        rule = Rule(
            name="test_rule",
            func=lambda line: ResultType(ResultTypeEnum.Ok),
            rule_type=RuleType.CPP_STYLE,
            rule_input_type=RuleInputType.LINE,
        )

        config = CppConfig(check_only_staged_files=False)
        run_cpp_checks([rule], config)
        # Should complete without error

    def test_run_cpp_checks_stops_on_error(
        self, tmp_path: Path, caplog: LogCaptureFixture
    ) -> None:
        """Test run_cpp_checks stops after first file with errors.

        Parameters
        ----------
        tmp_path: Path
            Temporary path for creating test files.
        caplog
            Pytest fixture for capturing log messages.

        """
        # Create test files
        file1 = tmp_path / "file1.cpp"
        file1.write_text("bad code\n")
        file2 = tmp_path / "file2.cpp"
        file2.write_text("more bad code\n")

        # Create a failing rule
        rule = Rule(
            name="failing_rule",
            func=lambda line: ResultType(ResultTypeEnum.Error, "Code error"),
            rule_type=RuleType.CPP_STYLE,
            rule_input_type=RuleInputType.LINE,
        )

        # Mock get_staged_files to return both files
        with patch(
            "devops.cpp.checks.get_staged_files", return_value=[file1, file2]
        ):
            config = CppConfig(check_only_staged_files=True)
            run_cpp_checks([rule], config)

        # Should log error for first file and stop
        error_logs = [
            record for record in caplog.records if record.levelname == "ERROR"
        ]
        assert len(error_logs) > 0
        assert any("Code error" in record.message for record in error_logs)

    def test_run_cpp_checks_skips_non_cpp_files(self, tmp_path: Path) -> None:
        """Test run_cpp_checks skips non-C++ files.

        Parameters
        ----------
        tmp_path: Path
            Temporary path for creating test files.

        """
        # Create mixed files
        cpp_file = tmp_path / "test.cpp"
        cpp_file.write_text("int main() {}\n")
        txt_file = tmp_path / "readme.txt"
        txt_file.write_text("documentation\n")

        call_count = [0]

        def counting_func(line: str) -> ResultType:
            call_count[0] += 1
            return ResultType(ResultTypeEnum.Ok)

        rule = Rule(
            name="counting_rule",
            func=counting_func,
            rule_type=RuleType.CPP_STYLE,
            rule_input_type=RuleInputType.LINE,
        )

        # Mock get_staged_files to return both files
        with patch(
            "devops.cpp.checks.get_staged_files", return_value=[cpp_file, txt_file]
        ):
            config = CppConfig(check_only_staged_files=True)
            run_cpp_checks([rule], config)

        # Should only process cpp file
        assert call_count[0] == 1  # Only one line in cpp_file

    def test_run_cpp_checks_with_file_rules(self, tmp_path: Path) -> None:
        """Test run_cpp_checks with file-based rules.

        Parameters
        ----------
        tmp_path: Path
            Temporary path for creating test files.

        """
        test_file = tmp_path / "test.cpp"
        test_file.write_text("int main() {}\n")

        # Create a file rule
        rule = Rule(
            name="file_rule",
            func=lambda content: ResultType(ResultTypeEnum.Ok),
            rule_type=RuleType.CPP_STYLE,
            rule_input_type=RuleInputType.FILE,
        )

        with patch("devops.cpp.checks.get_staged_files", return_value=[test_file]):
            config = CppConfig(check_only_staged_files=True)
            run_cpp_checks([rule], config)
            # Should complete without error

    def test_run_cpp_checks_with_mixed_rules(self, tmp_path: Path) -> None:
        """Test run_cpp_checks with both line and file rules.

        Parameters
        ----------
        tmp_path: Path
            Temporary path for creating test files.

        """
        test_file = tmp_path / "test.cpp"
        test_file.write_text("int main() {}\n")

        # Create line and file rules
        line_rule = Rule(
            name="line_rule",
            func=lambda line: ResultType(ResultTypeEnum.Ok),
            rule_type=RuleType.CPP_STYLE,
            rule_input_type=RuleInputType.LINE,
        )
        file_rule = Rule(
            name="file_rule",
            func=lambda content: ResultType(ResultTypeEnum.Ok),
            rule_type=RuleType.CPP_STYLE,
            rule_input_type=RuleInputType.FILE,
        )

        with patch("devops.cpp.checks.get_staged_files", return_value=[test_file]):
            config = CppConfig(check_only_staged_files=True)
            run_cpp_checks([line_rule, file_rule], config)
            # Should complete without error

    def test_run_cpp_checks_logs_checked_file(
        self, tmp_path: Path, caplog: LogCaptureFixture
    ) -> None:
        """Test run_cpp_checks logs the files being checked.

        Parameters
        ----------
        tmp_path: Path
            Temporary path for creating test files.
        caplog: LogCaptureFixture
            Pytest fixture for capturing log messages.

        """
        
        test_file = tmp_path / "test.cpp"
        test_file.write_text("int main() {}\n")

        rule = Rule(
            name="test_rule",
            func=lambda line: ResultType(ResultTypeEnum.Ok),
            rule_type=RuleType.CPP_STYLE,
            rule_input_type=RuleInputType.LINE,
        )

        with caplog.at_level(logging.DEBUG):
            with patch("devops.cpp.checks.get_staged_files", return_value=[test_file]):
                config = CppConfig(check_only_staged_files=True)
                run_cpp_checks([rule], config)

        # Should log the file being checked (at debug level)
        assert any(
            "Checking file" in record.message and str(test_file) in record.message
            for record in caplog.records
        )

    def test_run_cpp_checks_with_empty_rules_list(self, tmp_path: Path) -> None:
        """Test run_cpp_checks with empty rules list.

        Parameters
        ----------
        tmp_path: Path
            Temporary path for creating test files.

        """
        test_file = tmp_path / "test.cpp"
        test_file.write_text("int main() {}\n")

        with patch("devops.cpp.checks.get_staged_files", return_value=[test_file]):
            config = CppConfig(check_only_staged_files=True)
            run_cpp_checks([], config)
            # Should complete without error

    def test_run_cpp_checks_only_logs_errors(
        self, tmp_path: Path, caplog: LogCaptureFixture
    ) -> None:
        """Test run_cpp_checks only logs non-Ok results.

        Parameters
        ----------
        tmp_path: Path
            Temporary path for creating test files.
        caplog
            Pytest fixture for capturing log messages.

        """
        test_file = tmp_path / "test.cpp"
        test_file.write_text("line1\nline2\n")

        # Create a rule that fails on specific line
        def selective_rule(line: str) -> ResultType:
            if "line1" in line:
                return ResultType(ResultTypeEnum.Error, "Error on line1")
            return ResultType(ResultTypeEnum.Ok)

        rule = Rule(
            name="selective_rule",
            func=selective_rule,
            rule_type=RuleType.CPP_STYLE,
            rule_input_type=RuleInputType.LINE,
        )

        with patch("devops.cpp.checks.get_staged_files", return_value=[test_file]):
            config = CppConfig(check_only_staged_files=True)
            run_cpp_checks([rule], config)

        # Should only log the error, not the Ok result
        error_logs = [
            record
            for record in caplog.records
            if record.levelname == "ERROR" and "Error on line1" in record.message
        ]
        assert len(error_logs) == 1
