"""Tests for the NoGlobalUsing AST check."""

from __future__ import annotations

from pathlib import Path

import pytest

from devops.cpp.ast.checks.no_global_using import NoGlobalUsing
from devops.cpp.ast.engine import run_ast_checks

pytest.importorskip("clang.cindex")

_CHECK = [NoGlobalUsing()]
_ARGS = ["-std=c++17"]

# Namespace declarations reused across tests so libclang resolves the names.
_NS_DECLS = "namespace ns1 {}\nnamespace ns2 {}\n"


def _diags(code: str, tmp_path: Path) -> list[str]:
    p = tmp_path / "test.cpp"
    p.write_text(code)
    return [d.message for d in run_ast_checks(p, code, _ARGS, checks=_CHECK)]


class TestNoGlobalUsingDirective:
    """using namespace at global/namespace scope is flagged."""

    def test_global_using_namespace_flagged(self, tmp_path: Path) -> None:
        code = _NS_DECLS + "using namespace ns1;\n"
        diags = _diags(code, tmp_path)
        assert len(diags) == 1
        assert "using namespace ns1" in diags[0]

    def test_namespace_scoped_using_namespace_flagged(self, tmp_path: Path) -> None:
        code = _NS_DECLS + "namespace outer {\nusing namespace ns1;\n}\n"
        diags = _diags(code, tmp_path)
        assert len(diags) == 1
        assert "using namespace ns1" in diags[0]

    def test_using_namespace_in_function_allowed(self, tmp_path: Path) -> None:
        code = _NS_DECLS + "void f() {\nusing namespace ns1;\n}\n"
        assert _diags(code, tmp_path) == []

    def test_using_namespace_in_method_allowed(self, tmp_path: Path) -> None:
        code = _NS_DECLS + "struct S { void f() { using namespace ns1; } };\n"
        assert _diags(code, tmp_path) == []

    def test_multiple_global_directives_all_flagged(self, tmp_path: Path) -> None:
        code = _NS_DECLS + "using namespace ns1;\nusing namespace ns2;\n"
        diags = _diags(code, tmp_path)
        assert len(diags) == 2

    def test_mixed_scopes_only_global_flagged(self, tmp_path: Path) -> None:
        code = (
            _NS_DECLS
            + "using namespace ns1;\n"        # flagged
            + "void f() { using namespace ns2; }\n"  # ok
        )
        diags = _diags(code, tmp_path)
        assert len(diags) == 1
        assert "ns1" in diags[0]


class TestNoGlobalUsingDeclaration:
    """using X::Y at global/namespace scope is flagged."""

    def test_global_using_declaration_flagged(self, tmp_path: Path) -> None:
        code = "#include <vector>\nusing std::vector;\n"
        diags = _diags(code, tmp_path)
        assert len(diags) == 1
        assert "vector" in diags[0]

    def test_namespace_scoped_using_declaration_flagged(self, tmp_path: Path) -> None:
        code = "#include <vector>\nnamespace foo {\nusing std::vector;\n}\n"
        diags = _diags(code, tmp_path)
        assert len(diags) == 1

    def test_using_declaration_in_function_allowed(self, tmp_path: Path) -> None:
        code = "#include <vector>\nvoid f() {\nusing std::vector;\n}\n"
        assert _diags(code, tmp_path) == []

    def test_using_declaration_in_class_allowed(self, tmp_path: Path) -> None:
        code = "struct Base { void foo(); };\nstruct Derived : Base { using Base::foo; };\n"
        assert _diags(code, tmp_path) == []


class TestNoGlobalUsingCheckId:
    """The check id is correct and the check is selectable."""

    def test_check_id(self) -> None:
        assert NoGlobalUsing().id == "noGlobalUsing"

    def test_clean_file_produces_no_diagnostics(self, tmp_path: Path) -> None:
        code = _NS_DECLS + "void f() { using namespace ns1; }\n"
        assert _diags(code, tmp_path) == []
