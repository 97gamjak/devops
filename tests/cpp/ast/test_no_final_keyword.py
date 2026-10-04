"""Tests for the NoFinalKeyword AST check."""

from __future__ import annotations

import typing

import pytest

from devops.cpp.ast.checks.no_final_keyword import NoFinalKeyword
from devops.cpp.ast.engine import run_ast_checks

if typing.TYPE_CHECKING:
    from pathlib import Path

pytest.importorskip("clang.cindex")

_CHECK = [NoFinalKeyword()]
_ARGS = ["-std=c++17"]


def _diags(code: str, tmp_path: Path) -> list[str]:
    p = tmp_path / "test.cpp"
    p.write_text(code)
    return [d.message for d in run_ast_checks(p, code, _ARGS, checks=_CHECK)]


class TestNoFinalKeywordFlagged:
    """'final' on a class, struct, or virtual method is flagged."""

    def test_class_final_flagged(self, tmp_path: Path) -> None:
        """Test class final flagged."""
        code = "class Foo final {};\n"
        diags = _diags(code, tmp_path)
        assert len(diags) == 1
        assert "'final'" in diags[0]

    def test_struct_final_flagged(self, tmp_path: Path) -> None:
        """Test struct final flagged."""
        code = "struct Foo final {};\n"
        diags = _diags(code, tmp_path)
        assert len(diags) == 1

    def test_class_final_with_base_clause_flagged(self, tmp_path: Path) -> None:
        """Test class final with base clause flagged."""
        code = "struct Base {};\nclass Foo final : public Base {};\n"
        diags = _diags(code, tmp_path)
        assert len(diags) == 1

    def test_method_final_flagged(self, tmp_path: Path) -> None:
        """Test method final flagged."""
        code = (
            "struct Base { virtual void f(); };\n"
            "struct Foo : Base { void f() final; };\n"
        )
        diags = _diags(code, tmp_path)
        assert len(diags) == 1
        assert "method 'f'" in diags[0]

    def test_method_final_with_body_flagged(self, tmp_path: Path) -> None:
        """Test method final with body flagged."""
        code = (
            "struct Base { virtual void f(); };\n"
            "struct Foo : Base { void f() final {} };\n"
        )
        diags = _diags(code, tmp_path)
        assert len(diags) == 1

    def test_method_override_final_flagged(self, tmp_path: Path) -> None:
        """Test method override final flagged."""
        code = (
            "struct Base { virtual void f(); };\n"
            "struct Foo : Base { void f() override final; };\n"
        )
        diags = _diags(code, tmp_path)
        assert len(diags) == 1


class TestNoFinalKeywordAllowed:
    """Plain classes/structs/methods without 'final' are not flagged."""

    def test_class_allowed(self, tmp_path: Path) -> None:
        """Test class allowed."""
        code = "class Foo {};\n"
        assert _diags(code, tmp_path) == []

    def test_struct_with_base_clause_allowed(self, tmp_path: Path) -> None:
        """Test struct with base clause allowed."""
        code = "struct Base {};\nstruct Foo : Base {};\n"
        assert _diags(code, tmp_path) == []

    def test_method_override_allowed(self, tmp_path: Path) -> None:
        """Test method override allowed."""
        code = (
            "struct Base { virtual void f(); };\n"
            "struct Foo : Base { void f() override; };\n"
        )
        assert _diags(code, tmp_path) == []

    def test_parameter_named_final_allowed(self, tmp_path: Path) -> None:
        """Test parameter named final allowed."""
        code = "void f(int final);\n"
        assert _diags(code, tmp_path) == []

    def test_method_with_parameter_named_final_allowed(self, tmp_path: Path) -> None:
        """Test method with parameter named final allowed."""
        code = "struct Foo { void f(int final); };\n"
        assert _diags(code, tmp_path) == []


class TestNoFinalKeywordCheckId:
    """The check id is correct and the check is selectable."""

    def test_check_id(self) -> None:
        """Test check id."""
        assert NoFinalKeyword().id == "noFinalKeyword"

    def test_clean_file_produces_no_diagnostics(self, tmp_path: Path) -> None:
        """Test clean file produces no diagnostics."""
        code = "struct Base {};\nstruct Foo : Base { void f() override; };\n"
        assert _diags(code, tmp_path) == []
