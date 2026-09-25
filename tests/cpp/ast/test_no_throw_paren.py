"""Tests for the NoThrowParen AST check."""

from __future__ import annotations

import typing

import pytest

from devops.cpp.ast.checks.no_throw_paren import NoThrowParen
from devops.cpp.ast.engine import run_ast_checks

if typing.TYPE_CHECKING:
    from pathlib import Path

pytest.importorskip("clang.cindex")

_CHECK = [NoThrowParen()]
_ARGS = ["-std=c++17"]

_DECLS = "struct E { E(int); };\nint f(int);\n"


def _diags(code: str, tmp_path: Path) -> list[str]:
    p = tmp_path / "test.cpp"
    p.write_text(code)
    return [d.message for d in run_ast_checks(p, code, _ARGS, checks=_CHECK)]


class TestNoThrowParenFlagged:
    """throw(...) wrapping the whole thrown expression is flagged."""

    def test_throw_paren_variable_flagged(self, tmp_path: Path) -> None:
        """Test throw paren variable flagged."""
        code = "void g() { int x = 1; throw(x); }\n"
        diags = _diags(code, tmp_path)
        assert len(diags) == 1
        assert "throw(...)" in diags[0]

    def test_throw_paren_constructor_flagged(self, tmp_path: Path) -> None:
        """Test throw paren constructor flagged."""
        code = _DECLS + "void g() { throw(E(1)); }\n"
        diags = _diags(code, tmp_path)
        assert len(diags) == 1

    def test_throw_paren_expression_flagged(self, tmp_path: Path) -> None:
        """Test throw paren expression flagged."""
        code = "void g() { int x = 1; throw (x + 1); }\n"
        diags = _diags(code, tmp_path)
        assert len(diags) == 1

    def test_throw_double_paren_flagged(self, tmp_path: Path) -> None:
        """Test throw double paren flagged."""
        code = "void g() { int x = 1; throw((x)); }\n"
        diags = _diags(code, tmp_path)
        assert len(diags) == 1


class TestNoThrowParenAllowed:
    """Plain throws and calls whose own parens don't wrap the whole expression."""

    def test_throw_bare_variable_allowed(self, tmp_path: Path) -> None:
        """Test throw bare variable allowed."""
        code = "void g() { int x = 1; throw x; }\n"
        assert _diags(code, tmp_path) == []

    def test_throw_constructor_call_allowed(self, tmp_path: Path) -> None:
        """Test throw constructor call allowed."""
        code = _DECLS + "void g() { throw E(1); }\n"
        assert _diags(code, tmp_path) == []

    def test_rethrow_allowed(self, tmp_path: Path) -> None:
        """Test rethrow allowed."""
        code = "void g() { try {} catch (...) { throw; } }\n"
        assert _diags(code, tmp_path) == []

    def test_throw_call_expression_allowed(self, tmp_path: Path) -> None:
        """Test throw call expression allowed."""
        code = _DECLS + "void g() { throw f(1); }\n"
        assert _diags(code, tmp_path) == []


class TestNoThrowParenCheckId:
    """The check id is correct and the check is selectable."""

    def test_check_id(self) -> None:
        """Test check id."""
        assert NoThrowParen().id == "noThrowParen"

    def test_clean_file_produces_no_diagnostics(self, tmp_path: Path) -> None:
        """Test clean file produces no diagnostics."""
        code = _DECLS + "void g() { throw E(1); }\n"
        assert _diags(code, tmp_path) == []
