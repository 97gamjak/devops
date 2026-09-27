"""Tests for the AST-check engine's parse-failure handling."""

from __future__ import annotations

import typing

import pytest

from devops.cpp.ast.checks.no_global_using import NoGlobalUsing
from devops.cpp.ast.engine import (
    _extract_plain_include,
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


class TestExtractPlainInclude:
    """Unit tests for pulling a bare -include <file> out of compile args."""

    def test_extracts_flag_and_file(self) -> None:
        """Test extracts flag and file."""
        args, file = _extract_plain_include(["-std=c++17", "-include", "/pch.hxx"])
        assert file == "/pch.hxx"
        assert args == ["-std=c++17"]

    def test_absent_returns_unchanged_args_and_none(self) -> None:
        """Test absent returns unchanged args and none."""
        args = ["-std=c++17", "-Wall"]
        result_args, file = _extract_plain_include(args)
        assert file is None
        assert result_args == args

    def test_dangling_include_with_no_file_is_a_noop(self) -> None:
        """A trailing -include with nothing after it is left alone, not crashed on."""
        args = ["-std=c++17", "-include"]
        result_args, file = _extract_plain_include(args)
        assert file is None
        assert result_args == args


class TestPreludeIncludeWrapping:
    """A bare -include <file> is routed through a wrapper #include, not the flag.

    Regression coverage for a real bug: pip's libclang build was observed to
    hard-crash (TranslationUnitLoadError, no diagnostics at all) parsing some
    real PCH headers when force-included via the `-include` compiler flag,
    even though the identical header content parses cleanly as an ordinary
    `#include`, and even though the project's own real compiler parses the
    same `-include` flag with no problem at all. The engine now strips a
    bare `-include <file>` out of compile_args and instead prepends a real
    `#include` line ahead of the checked file in a synthetic wrapper — same
    as the existing header-check wrapper technique — which avoids the crash.
    """

    def test_prelude_include_is_processed_and_does_not_crash(
        self, tmp_path: Path
    ) -> None:
        """Test prelude include is processed and does not crash."""
        prelude = tmp_path / "prelude.hpp"
        prelude.write_text("using PreludeInt = int;\n")

        p = tmp_path / "test.cpp"
        code = "PreludeInt x = 0;\nvoid f() { (void)x; }\n"
        p.write_text(code)

        diags = run_ast_checks(
            p, code, ["-std=c++17", "-include", str(prelude)], checks=[]
        )
        assert diags == []

    def test_diagnostics_keep_the_real_file_and_original_line_numbers(
        self, tmp_path: Path
    ) -> None:
        """Line numbers/paths for the real file are unaffected by the wrapper."""
        prelude = tmp_path / "prelude.hpp"
        prelude.write_text("namespace unrelated {}\n")

        p = tmp_path / "test.cpp"
        code = "namespace ns1 {}\nusing namespace ns1;\n"
        p.write_text(code)

        diags = run_ast_checks(
            p,
            code,
            ["-std=c++17", "-include", str(prelude)],
            checks=[NoGlobalUsing()],
        )
        assert len(diags) == 1
        assert diags[0].file == str(p)
        assert diags[0].line == 2

    def test_missing_prelude_file_reports_ast_parse_error_not_a_crash(
        self, tmp_path: Path
    ) -> None:
        """A prelude file that doesn't exist fails as a normal diagnostic."""
        p = tmp_path / "test.cpp"
        code = "void f() {}\n"
        p.write_text(code)

        diags = run_ast_checks(
            p,
            code,
            ["-std=c++17", "-include", str(tmp_path / "does_not_exist.hpp")],
            checks=[],
        )
        assert any(d.check_id == "astParseError" for d in diags)
