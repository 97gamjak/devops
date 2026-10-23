"""Tests for the EnforceTypenameOverClass AST check."""

from __future__ import annotations

import typing

import pytest

from devops.cpp.ast.checks.enforce_typename_over_class import EnforceTypenameOverClass
from devops.cpp.ast.engine import run_ast_checks

if typing.TYPE_CHECKING:
    from pathlib import Path

pytest.importorskip("clang.cindex")

_CHECK = [EnforceTypenameOverClass()]
_ARGS = ["-std=c++17"]


def _diags(code: str, tmp_path: Path) -> list[str]:
    p = tmp_path / "test.cpp"
    p.write_text(code)
    return [d.message for d in run_ast_checks(p, code, _ARGS, checks=_CHECK)]


class TestEnforceTypenameOverClassFlagged:
    """A template type parameter spelled 'class' is flagged."""

    def test_class_template_flagged(self, tmp_path: Path) -> None:
        """Test class template flagged."""
        code = "template <class T>\nvoid f(T t);\n"
        diags = _diags(code, tmp_path)
        assert len(diags) == 1
        assert "'T'" in diags[0]

    def test_class_template_class_decl_flagged(self, tmp_path: Path) -> None:
        """Test class template on a class declaration flagged."""
        code = "template <class T>\nclass Foo { T t; };\n"
        diags = _diags(code, tmp_path)
        assert len(diags) == 1

    def test_variadic_class_template_flagged(self, tmp_path: Path) -> None:
        """Test variadic class template flagged."""
        code = "template <class... Args>\nvoid f(Args... args);\n"
        diags = _diags(code, tmp_path)
        assert len(diags) == 1

    def test_multiple_class_params_flagged(self, tmp_path: Path) -> None:
        """Test multiple class params flagged."""
        code = "template <class T, class U>\nvoid f(T t, U u);\n"
        diags = _diags(code, tmp_path)
        assert len(diags) == 2

    def test_mixed_class_and_typename_flags_only_class(self, tmp_path: Path) -> None:
        """Test mixed class and typename flags only the class one."""
        code = "template <typename T, class U>\nvoid f(T t, U u);\n"
        diags = _diags(code, tmp_path)
        assert len(diags) == 1
        assert "'U'" in diags[0]


class TestEnforceTypenameOverClassAllowed:
    """A template type parameter spelled 'typename' is not flagged."""

    def test_typename_template_allowed(self, tmp_path: Path) -> None:
        """Test typename template allowed."""
        code = "template <typename T>\nvoid f(T t);\n"
        assert _diags(code, tmp_path) == []

    def test_variadic_typename_template_allowed(self, tmp_path: Path) -> None:
        """Test variadic typename template allowed."""
        code = "template <typename... Args>\nvoid f(Args... args);\n"
        assert _diags(code, tmp_path) == []

    def test_plain_class_declaration_allowed(self, tmp_path: Path) -> None:
        """Test plain, non-template class declaration allowed."""
        code = "class Foo {};\n"
        assert _diags(code, tmp_path) == []

    def test_non_type_template_param_allowed(self, tmp_path: Path) -> None:
        """Test non-type template param allowed."""
        code = "template <int N>\nvoid f();\n"
        assert _diags(code, tmp_path) == []


class TestEnforceTypenameOverClassCheckId:
    """The check id is correct and the check is selectable."""

    def test_check_id(self) -> None:
        """Test check id."""
        assert EnforceTypenameOverClass().id == "enforceTypenameOverClass"

    def test_clean_file_produces_no_diagnostics(self, tmp_path: Path) -> None:
        """Test clean file produces no diagnostics."""
        code = "template <typename T>\nclass Foo { T t; };\n"
        assert _diags(code, tmp_path) == []
