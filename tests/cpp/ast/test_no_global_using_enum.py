"""Tests for the NoGlobalUsingEnum AST check."""

from __future__ import annotations

from pathlib import Path

import pytest

from devops.config.base import ConfigError
from devops.cpp.ast.checks.no_global_using import NoGlobalUsing
from devops.cpp.ast.checks.no_global_using_enum import NoGlobalUsingEnum
from devops.cpp.ast.engine import run_ast_checks

pytest.importorskip("clang.cindex")

_ARGS = ["-std=c++23"]
_DECLS = (
    "namespace molsys { enum class HybridZone { A, B };"
    " enum class Other { C }; enum class Fwd : int; }\n"
)


def _diags(code: str, tmp_path: Path, config: dict | None = None) -> list[str]:
    check = NoGlobalUsingEnum()
    if config is not None:
        check.configure(config)
    p = tmp_path / "test.cpp"
    p.write_text(code)
    return [d.message for d in run_ast_checks(p, code, _ARGS, checks=[check])]


class TestNoGlobalUsingEnum:
    """using enum at global/namespace scope is flagged."""

    def test_check_id(self) -> None:
        assert NoGlobalUsingEnum().id == "noGlobalUsingEnum"

    def test_global_using_enum_flagged(self, tmp_path: Path) -> None:
        diags = _diags(_DECLS + "using enum molsys::HybridZone;\n", tmp_path)
        assert len(diags) == 1
        assert "using enum molsys::HybridZone'" in diags[0]

    def test_namespace_scoped_using_enum_flagged(self, tmp_path: Path) -> None:
        code = _DECLS + "namespace n { using enum molsys::HybridZone; }\n"
        assert len(_diags(code, tmp_path)) == 1

    def test_using_enum_in_function_allowed(self, tmp_path: Path) -> None:
        code = _DECLS + "void f() { using enum molsys::HybridZone; }\n"
        assert _diags(code, tmp_path) == []

    def test_using_enum_in_class_allowed(self, tmp_path: Path) -> None:
        code = _DECLS + "struct S { using enum molsys::HybridZone; };\n"
        assert _diags(code, tmp_path) == []

    def test_enum_definitions_and_forward_declarations_not_flagged(
        self, tmp_path: Path
    ) -> None:
        code = "enum class A { X };\nenum class B : int;\nenum C { Y };\n" + _DECLS
        assert _diags(code, tmp_path) == []

    def test_using_namespace_and_declaration_not_flagged(self, tmp_path: Path) -> None:
        code = _DECLS + "using namespace molsys;\nusing molsys::HybridZone;\n"
        assert _diags(code, tmp_path) == []

    def test_noglobalusing_ignores_using_enum(self, tmp_path: Path) -> None:
        code = _DECLS + "using enum molsys::HybridZone;\n"
        p = tmp_path / "test.cpp"
        p.write_text(code)
        assert run_ast_checks(p, code, _ARGS, checks=[NoGlobalUsing()]) == []

    def test_leading_double_colon_normalised(self, tmp_path: Path) -> None:
        diags = _diags(_DECLS + "using enum ::molsys::HybridZone;\n", tmp_path)
        assert "using enum molsys::HybridZone'" in diags[0]


class TestNameFilters:
    """enabled_names / disabled_names select which enums are reported."""

    _CODE = _DECLS + "using enum molsys::HybridZone;\nusing enum molsys::Other;\n"

    def test_enabled_names_is_an_allowlist(self, tmp_path: Path) -> None:
        diags = _diags(self._CODE, tmp_path, {"enabled_names": ["molsys::Other"]})
        assert len(diags) == 1
        assert "molsys::Other" in diags[0]

    def test_disabled_names_are_skipped(self, tmp_path: Path) -> None:
        diags = _diags(self._CODE, tmp_path, {"disabled_names": ["molsys::Other"]})
        assert len(diags) == 1
        assert "molsys::HybridZone" in diags[0]

    def test_disabled_wins_over_enabled(self, tmp_path: Path) -> None:
        config = {
            "enabled_names": ["molsys::Other"],
            "disabled_names": ["molsys::Other"],
        }
        assert _diags(self._CODE, tmp_path, config) == []

    def test_invalid_config_raises(self) -> None:
        with pytest.raises(ConfigError, match="noGlobalUsingEnum"):
            NoGlobalUsingEnum().configure({"enabled_names": "molsys::Other"})
