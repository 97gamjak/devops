"""Tests for ASTChecksRule, the Rule adapter around the AST-check engine."""

from __future__ import annotations

import typing

import pytest

from devops.cpp.ast.rule import ASTChecksRule
from devops.rules import FileRuleInput, ResultTypeEnum

if typing.TYPE_CHECKING:
    from pathlib import Path

pytest.importorskip("clang.cindex")


class TestASTChecksRule:
    """Tests for ASTChecksRule."""

    def test_ok_on_clean_file(self, tmp_path: Path) -> None:
        """A file with no violations returns Ok.

        Parameters
        ----------
        tmp_path: Path
            Temporary path for creating test files.

        """
        cpp_file = tmp_path / "clean.cpp"
        content = "struct SimulationBox {};\nvoid foo(SimulationBox simulationBox) {}\n"
        cpp_file.write_text(content)

        rule = ASTChecksRule()
        result = rule.apply(FileRuleInput(file_content=content, path=cpp_file))

        assert result.value == ResultTypeEnum.Ok

    def test_error_on_violation(self, tmp_path: Path) -> None:
        """A file with a violation returns an Error with a description.

        Parameters
        ----------
        tmp_path: Path
            Temporary path for creating test files.

        """
        cpp_file = tmp_path / "bad.cpp"
        content = "struct SimulationBox {};\nvoid foo(SimulationBox simBox) {}\n"
        cpp_file.write_text(content)

        rule = ASTChecksRule()
        result = rule.apply(FileRuleInput(file_content=content, path=cpp_file))

        assert result.value == ResultTypeEnum.Error
        assert "simBox" in result.description
        assert "paramNameForType" in result.description

    def test_ok_when_path_missing(self) -> None:
        """No path means nothing to parse, so the rule returns Ok."""
        rule = ASTChecksRule()
        result = rule.apply(FileRuleInput(file_content="void foo() {}", path=None))

        assert result.value == ResultTypeEnum.Ok
