"""Tests for the NoGlobalUsing AST check."""

from __future__ import annotations

import typing

import pytest

from devops.config.base import ConfigError
from devops.cpp.ast.checks.no_global_using import NoGlobalUsing
from devops.cpp.ast.engine import run_ast_checks

if typing.TYPE_CHECKING:
    from pathlib import Path

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
        """Test global using namespace flagged."""
        code = _NS_DECLS + "using namespace ns1;\n"
        diags = _diags(code, tmp_path)
        assert len(diags) == 1
        assert "using namespace ns1" in diags[0]

    def test_namespace_scoped_using_namespace_flagged(self, tmp_path: Path) -> None:
        """Test namespace scoped using namespace flagged."""
        code = _NS_DECLS + "namespace outer {\nusing namespace ns1;\n}\n"
        diags = _diags(code, tmp_path)
        assert len(diags) == 1
        assert "using namespace ns1" in diags[0]

    def test_using_namespace_in_function_allowed(self, tmp_path: Path) -> None:
        """Test using namespace in function allowed."""
        code = _NS_DECLS + "void f() {\nusing namespace ns1;\n}\n"
        assert _diags(code, tmp_path) == []

    def test_using_namespace_in_method_allowed(self, tmp_path: Path) -> None:
        """Test using namespace in method allowed."""
        code = _NS_DECLS + "struct S { void f() { using namespace ns1; } };\n"
        assert _diags(code, tmp_path) == []

    def test_multiple_global_directives_all_flagged(self, tmp_path: Path) -> None:
        """Test multiple global directives all flagged."""
        code = _NS_DECLS + "using namespace ns1;\nusing namespace ns2;\n"
        diags = _diags(code, tmp_path)
        assert len(diags) == 2

    def test_mixed_scopes_only_global_flagged(self, tmp_path: Path) -> None:
        """Test mixed scopes only global flagged."""
        code = (
            _NS_DECLS
            + "using namespace ns1;\n"  # flagged
            + "void f() { using namespace ns2; }\n"  # ok
        )
        diags = _diags(code, tmp_path)
        assert len(diags) == 1
        assert "ns1" in diags[0]


class TestNoGlobalUsingDeclaration:
    """using X::Y at global/namespace scope is flagged."""

    def test_global_using_declaration_flagged(self, tmp_path: Path) -> None:
        """Test global using declaration flagged."""
        code = "#include <vector>\nusing std::vector;\n"
        diags = _diags(code, tmp_path)
        assert len(diags) == 1
        assert "vector" in diags[0]

    def test_namespace_scoped_using_declaration_flagged(self, tmp_path: Path) -> None:
        """Test namespace scoped using declaration flagged."""
        code = "#include <vector>\nnamespace foo {\nusing std::vector;\n}\n"
        diags = _diags(code, tmp_path)
        assert len(diags) == 1

    def test_using_declaration_in_function_allowed(self, tmp_path: Path) -> None:
        """Test using declaration in function allowed."""
        code = "#include <vector>\nvoid f() {\nusing std::vector;\n}\n"
        assert _diags(code, tmp_path) == []

    def test_using_declaration_in_class_allowed(self, tmp_path: Path) -> None:
        """Test using declaration in class allowed."""
        code = (
            "struct Base { void foo(); };\n"
            "struct Derived : Base { using Base::foo; };\n"
        )
        assert _diags(code, tmp_path) == []


class TestNoGlobalUsingCheckId:
    """The check id is correct and the check is selectable."""

    def test_check_id(self) -> None:
        """Test check id."""
        assert NoGlobalUsing().id == "noGlobalUsing"

    def test_clean_file_produces_no_diagnostics(self, tmp_path: Path) -> None:
        """Test clean file produces no diagnostics."""
        code = _NS_DECLS + "void f() { using namespace ns1; }\n"
        assert _diags(code, tmp_path) == []


class TestNameFilters:
    """enabled_names / disabled_names restrict which usings are reported."""

    _CODE = (
        "namespace a { namespace b { struct S {}; } struct T {}; }\n"
        "namespace c {}\n"
        "using namespace a::b;\n"
        "using namespace c;\n"
        "using a::T;\n"
    )

    @staticmethod
    def _run(code: str, tmp_path: Path, config: dict) -> list[str]:
        check = NoGlobalUsing()
        check.configure(config)
        p = tmp_path / "test.cpp"
        p.write_text(code)
        return [d.message for d in run_ast_checks(p, code, _ARGS, checks=[check])]

    def test_default_flags_everything_with_qualified_names(
        self, tmp_path: Path
    ) -> None:
        """Test default flags everything with qualified names."""
        diags = self._run(self._CODE, tmp_path, {})
        assert len(diags) == 3
        assert "using namespace a::b'" in diags[0]
        assert "using a::T'" in diags[2]

    def test_enabled_names_is_an_allowlist(self, tmp_path: Path) -> None:
        """Test enabled names is an allowlist."""
        diags = self._run(self._CODE, tmp_path, {"enabled_names": ["c"]})
        assert len(diags) == 1
        assert "using namespace c'" in diags[0]

    def test_disabled_names_are_skipped(self, tmp_path: Path) -> None:
        """Test disabled names are skipped."""
        diags = self._run(self._CODE, tmp_path, {"disabled_names": ["a::b", "a::T"]})
        assert len(diags) == 1
        assert "using namespace c'" in diags[0]

    def test_disabled_names_win_over_enabled_names(self, tmp_path: Path) -> None:
        """Test disabled names win over enabled names."""
        config = {"enabled_names": ["c", "a::T"], "disabled_names": ["c"]}
        diags = self._run(self._CODE, tmp_path, config)
        assert len(diags) == 1
        assert "using a::T'" in diags[0]

    def test_names_match_exactly_not_by_prefix(self, tmp_path: Path) -> None:
        """Test names match exactly not by prefix."""
        assert len(self._run(self._CODE, tmp_path, {"enabled_names": ["a"]})) == 0

    def test_leading_double_colon_is_ignored(self, tmp_path: Path) -> None:
        """Test leading double colon is ignored."""
        diags = self._run(self._CODE, tmp_path, {"enabled_names": ["::c"]})
        assert len(diags) == 1

    @pytest.mark.parametrize("bad", ["std", ["std", 1], {"std": True}])
    @pytest.mark.parametrize("key", ["enabled_names", "disabled_names"])
    def test_invalid_config_raises(self, key: str, bad: object) -> None:
        """Test invalid config raises."""
        with pytest.raises(ConfigError, match=key):
            NoGlobalUsing().configure({key: bad})
