"""Tests for the MacroReplacement AST check."""

from __future__ import annotations

import typing

import pytest

from devops.config.base import ConfigError
from devops.cpp.ast.checks.macro_replacement import MacroReplacement
from devops.cpp.ast.engine import run_ast_checks

if typing.TYPE_CHECKING:
    from pathlib import Path

pytest.importorskip("clang.cindex")

_ARGS = ["-std=c++17"]

_MACRO_DEFS = (
    "#define EXPECT_THROW(stmt, ex) do { stmt; } while(0)\n"
    "#define EXPECT_THROW_MSG(stmt, ex, msg) do { stmt; } while(0)\n"
    "#define ASSERT_THROW(stmt, ex) do { stmt; } while(0)\n"
    "#define ASSERT_THROW_MSG(stmt, ex, msg) do { stmt; } while(0)\n"
)


def _diags(
    code: str, tmp_path: Path, check: MacroReplacement | None = None
) -> list[str]:
    p = tmp_path / "test.cpp"
    p.write_text(code)
    checks = [check or MacroReplacement()]
    return [d.message for d in run_ast_checks(p, code, _ARGS, checks=checks)]


class TestMacroReplacementDefaults:
    """The built-in default mapping flags EXPECT_THROW/ASSERT_THROW."""

    def test_expect_throw_flagged(self, tmp_path: Path) -> None:
        """Test expect throw flagged."""
        code = _MACRO_DEFS + "void f() { EXPECT_THROW(throw 1, int); }\n"
        diags = _diags(code, tmp_path)
        assert len(diags) == 1
        assert "EXPECT_THROW" in diags[0]
        assert "EXPECT_THROW_MSG" in diags[0]

    def test_assert_throw_flagged(self, tmp_path: Path) -> None:
        """Test assert throw flagged."""
        code = _MACRO_DEFS + "void f() { ASSERT_THROW(throw 1, int); }\n"
        diags = _diags(code, tmp_path)
        assert len(diags) == 1
        assert "ASSERT_THROW" in diags[0]
        assert "ASSERT_THROW_MSG" in diags[0]

    def test_msg_variants_allowed(self, tmp_path: Path) -> None:
        """Test msg variants allowed."""
        code = (
            _MACRO_DEFS
            + 'void f() { EXPECT_THROW_MSG(throw 1, int, "m"); '
            + 'ASSERT_THROW_MSG(throw 1, int, "m"); }\n'
        )
        assert _diags(code, tmp_path) == []

    def test_macro_defined_in_included_header_still_flagged(
        self, tmp_path: Path
    ) -> None:
        """Test macro defined in included header still flagged."""
        header = tmp_path / "gtest_stub.hpp"
        header.write_text(_MACRO_DEFS)
        code = '#include "gtest_stub.hpp"\nvoid f() { EXPECT_THROW(throw 1, int); }\n'
        diags = _diags(code, tmp_path)
        assert len(diags) == 1
        assert "EXPECT_THROW" in diags[0]

    def test_clean_file_produces_no_diagnostics(self, tmp_path: Path) -> None:
        """Test clean file produces no diagnostics."""
        code = _MACRO_DEFS + "void f() {}\n"
        assert _diags(code, tmp_path) == []


class TestMacroReplacementCheckId:
    """The check id is correct."""

    def test_check_id(self) -> None:
        """Test check id."""
        assert MacroReplacement().id == "macroReplacement"


class TestMacroReplacementConfig:
    """macro_to_replacement replaces the built-in default mapping."""

    def test_custom_mapping_replaces_default(self, tmp_path: Path) -> None:
        """Test custom mapping replaces default."""
        check = MacroReplacement()
        check.configure({"macro_to_replacement": {"EXPECT_EQ": "EXPECT_EQ_MSG"}})
        code = (
            "#define EXPECT_THROW(a, b) do {} while(0)\n"
            "#define EXPECT_EQ(a, b) do {} while(0)\n"
            "void f() { EXPECT_THROW(1, 2); EXPECT_EQ(1, 2); }\n"
        )
        diags = _diags(code, tmp_path, check)
        assert len(diags) == 1
        assert "EXPECT_EQ" in diags[0]

    def test_missing_key_keeps_default_mapping(self, tmp_path: Path) -> None:
        """Test missing key keeps default mapping."""
        check = MacroReplacement()
        check.configure({})
        code = _MACRO_DEFS + "void f() { EXPECT_THROW(throw 1, int); }\n"
        diags = _diags(code, tmp_path, check)
        assert len(diags) == 1

    @pytest.mark.parametrize(
        "bad", [["not", "a", "dict"], {"EXPECT_THROW": 1}, {1: "EXPECT_THROW_MSG"}]
    )
    def test_invalid_config_raises(self, bad: object) -> None:
        """Test invalid config raises."""
        with pytest.raises(ConfigError, match="macro_to_replacement"):
            MacroReplacement().configure({"macro_to_replacement": bad})
