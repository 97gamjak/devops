"""Tests for cpp_checks CLI script."""

from __future__ import annotations

import typing
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from devops.scripts.cpp_checks import app

if typing.TYPE_CHECKING:
    from pathlib import Path

runner = CliRunner()


class TestCppChecksCLI:
    """Tests for cpp_checks Typer CLI command."""

    def test_cpp_checks_command_exists(self) -> None:
        """Test that cpp_checks command is registered."""
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "C++ code quality checks" in result.stdout

    def test_cpp_checks_runs_without_license_header_arg(self) -> None:
        """Test cpp_checks command runs without license_header argument."""
        with (
            patch("devops.scripts.cpp_checks.build_cpp_rules") as mock_build,
            patch("devops.scripts.cpp_checks.run_cpp_checks") as mock_run,
        ):
            mock_build.return_value = []
            mock_run.return_value = None

            result = runner.invoke(app, ["cpp-checks"])
            
            # Command should execute successfully
            assert result.exit_code == 0
            # Should call build_cpp_rules and run_cpp_checks
            assert mock_build.called
            assert mock_run.called

    def test_cpp_checks_with_license_header_argument(self, tmp_path: Path) -> None:
        """Test cpp_checks command with license_header argument.

        Parameters
        ----------
        tmp_path: Path
            Temporary path for creating test files.

        """
        # Create a license header file
        header_file = tmp_path / "header.txt"
        header_file.write_text("// Copyright\n")

        with (
            patch("devops.scripts.cpp_checks.build_cpp_rules") as mock_build,
            patch("devops.scripts.cpp_checks.run_cpp_checks") as mock_run,
        ):
            mock_build.return_value = []
            mock_run.return_value = None

            result = runner.invoke(app, ["cpp-checks", str(header_file)])
            
            # Command should execute successfully
            assert result.exit_code == 0
            # Should call with the provided header file
            assert mock_build.called
            call_config = mock_build.call_args[0][0]
            assert call_config.license_header == str(header_file)

    def test_cpp_checks_uses_global_config_when_no_arg(self) -> None:
        """Test cpp_checks uses global config when no license_header provided."""
        with (
            patch("devops.scripts.cpp_checks.build_cpp_rules") as mock_build,
            patch("devops.scripts.cpp_checks.run_cpp_checks") as mock_run,
            patch("devops.scripts.cpp_checks.__GLOBAL_CONFIG__") as mock_config,
        ):
            mock_build.return_value = []
            mock_run.return_value = None
            mock_config.cpp.license_header = "/default/header.txt"

            result = runner.invoke(app, ["cpp-checks"])
            
            assert result.exit_code == 0
            # Should use the global config's license_header
            assert mock_build.called

    def test_cpp_checks_passes_config_to_run_cpp_checks(self) -> None:
        """Test cpp_checks passes configuration to run_cpp_checks."""
        with (
            patch("devops.scripts.cpp_checks.build_cpp_rules") as mock_build,
            patch("devops.scripts.cpp_checks.run_cpp_checks") as mock_run,
        ):
            mock_build.return_value = []
            mock_run.return_value = None

            result = runner.invoke(app, ["cpp-checks"])
            
            assert result.exit_code == 0
            # Should pass config to run_cpp_checks
            assert mock_run.called
            assert len(mock_run.call_args[0]) == 2  # rules and config

    def test_cpp_checks_passes_rules_to_run_cpp_checks(self) -> None:
        """Test cpp_checks passes rules to run_cpp_checks."""
        with (
            patch("devops.scripts.cpp_checks.build_cpp_rules") as mock_build,
            patch("devops.scripts.cpp_checks.run_cpp_checks") as mock_run,
        ):
            mock_rules = [MagicMock(), MagicMock()]
            mock_build.return_value = mock_rules
            mock_run.return_value = None

            result = runner.invoke(app, ["cpp-checks"])
            
            assert result.exit_code == 0
            # Should pass the rules from build_cpp_rules to run_cpp_checks
            assert mock_run.called
            assert mock_run.call_args[0][0] == mock_rules

    def test_cpp_checks_creates_config_with_replace(self) -> None:
        """Test cpp_checks creates config using dataclass replace."""
        with (
            patch("devops.scripts.cpp_checks.build_cpp_rules") as mock_build,
            patch("devops.scripts.cpp_checks.run_cpp_checks") as mock_run,
            patch("devops.scripts.cpp_checks.replace") as mock_replace,
            patch("devops.scripts.cpp_checks.__GLOBAL_CONFIG__") as mock_global,
        ):
            mock_build.return_value = []
            mock_run.return_value = None
            mock_replace.return_value = MagicMock()

            result = runner.invoke(app, ["cpp-checks", "/path/to/header.txt"])
            
            assert result.exit_code == 0
            # Should use replace to create new config
            assert mock_replace.called
            # First argument should be the global cpp config
            assert mock_replace.call_args[0][0] == mock_global.cpp
            # Should specify license_header in kwargs
            assert mock_replace.call_args[1]["license_header"] == "/path/to/header.txt"

    def test_cpp_checks_command_name(self) -> None:
        """Test cpp_checks command has correct name in CLI."""
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        # Check that cpp-checks command is listed
        assert "cpp-checks" in result.stdout
