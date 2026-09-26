"""Tests for the AST-check engine's parse-failure handling."""

from __future__ import annotations

import typing

import pytest

from devops.cpp.ast.checks.no_global_using import NoGlobalUsing
from devops.cpp.ast.engine import (
    _has_resource_dir,
    _with_auto_resource_dir,
    _with_fallback_resource_dir,
    run_ast_checks,
)

if typing.TYPE_CHECKING:
    from pathlib import Path

pytest.importorskip("clang.cindex")


class TestFatalParseErrorSurfaced:
    """A fatal libclang diagnostic is reported as an astParseError."""

    def test_unresolvable_include_reports_ast_parse_error(self, tmp_path: Path) -> None:
        """Test unresolvable include reports ast parse error."""
        p = tmp_path / "test.cpp"
        code = '#include "does_not_exist_anywhere.hpp"\nvoid f() {}\n'
        p.write_text(code)
        diags = run_ast_checks(p, code, ["-std=c++17"], checks=[])
        assert any(d.check_id == "astParseError" for d in diags)

    def test_clean_file_has_no_ast_parse_error(self, tmp_path: Path) -> None:
        """Test clean file has no ast parse error."""
        p = tmp_path / "test.cpp"
        code = "void f() {}\n"
        p.write_text(code)
        diags = run_ast_checks(p, code, ["-std=c++17"], checks=[])
        assert not any(d.check_id == "astParseError" for d in diags)

    def test_checks_still_run_on_the_parsed_prefix(self, tmp_path: Path) -> None:
        """A fatal error doesn't suppress diagnostics found before it fires."""
        p = tmp_path / "test.cpp"
        code = (
            "namespace ns1 {}\n"
            "using namespace ns1;\n"
            '#include "does_not_exist_anywhere.hpp"\n'
        )
        p.write_text(code)
        diags = run_ast_checks(p, code, ["-std=c++17"], checks=[NoGlobalUsing()])
        assert any(d.check_id == "noGlobalUsing" for d in diags)


class TestResourceDirHelpers:
    """Unit tests for the -resource-dir detection/injection helpers."""

    def test_has_resource_dir_detects_equals_form(self) -> None:
        """Test has resource dir detects equals form."""
        assert _has_resource_dir(["-std=c++17", "-resource-dir=/foo"])

    def test_has_resource_dir_detects_separate_form(self) -> None:
        """Test has resource dir detects separate form."""
        assert _has_resource_dir(["-resource-dir", "/foo"])

    def test_has_resource_dir_false_when_absent(self) -> None:
        """Test has resource dir false when absent."""
        assert not _has_resource_dir(["-std=c++17"])

    def test_with_auto_resource_dir_leaves_existing_untouched(self) -> None:
        """Test with auto resource dir leaves existing untouched."""
        args = ["-resource-dir=/already/set"]
        assert _with_auto_resource_dir(args, "clang++") == args

    def test_with_auto_resource_dir_unknown_compiler_is_noop(self) -> None:
        """An unresolvable compiler leaves args unchanged rather than erroring."""
        args = ["-std=c++17"]
        result = _with_auto_resource_dir(args, "not-a-real-compiler-xyz")
        assert result == args

    def test_with_fallback_resource_dir_leaves_existing_untouched(self) -> None:
        """Test with fallback resource dir leaves existing untouched."""
        args = ["-resource-dir=/already/set"]
        assert _with_fallback_resource_dir(args) == args
