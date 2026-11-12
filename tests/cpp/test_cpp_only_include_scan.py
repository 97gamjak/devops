"""Tests for the plain-text cpp-only-include scanning helpers."""

from __future__ import annotations

from devops.cpp.cpp_only_include_scan import (
    find_includes,
    matches_cpp_only_header,
    scan_text_for_violations,
)


class TestFindIncludes:
    """Tests for find_includes."""

    def test_finds_quoted_and_angle_includes(self) -> None:
        """Test both quoted and angle-bracket includes are found with line numbers."""
        content = '#include "a/b.hpp"\n#include <c/d.hpp>\nint x;\n'
        assert find_includes(content) == [(1, "a/b.hpp"), (2, "c/d.hpp")]

    def test_ignores_non_include_lines(self) -> None:
        """Test lines without a #include directive are ignored."""
        content = "int x;\n// #include commented out in a trailing position\n"
        assert find_includes(content) == []

    def test_indented_include_is_found(self) -> None:
        """Test a leading-whitespace #include (e.g. inside an #ifdef) is found."""
        content = '#ifdef FOO\n  #include "a.hpp"\n#endif\n'
        assert find_includes(content) == [(2, "a.hpp")]


class TestMatchesCppOnlyHeader:
    """Tests for matches_cpp_only_header."""

    def test_full_path_match(self) -> None:
        """Test an exact full-path pattern matches."""
        assert matches_cpp_only_header("detail/foo_impl.hpp", ["detail/foo_impl.hpp"])

    def test_basename_glob_match(self) -> None:
        """Test a basename glob pattern matches regardless of directory."""
        assert matches_cpp_only_header("detail/foo_impl.hpp", ["*_impl.hpp"])

    def test_no_match(self) -> None:
        """Test an unrelated path does not match."""
        assert not matches_cpp_only_header("bar.hpp", ["detail/foo_impl.hpp"])

    def test_empty_headers_never_matches(self) -> None:
        """Test an empty pattern list never matches anything."""
        assert not matches_cpp_only_header("detail/foo_impl.hpp", [])


class TestScanTextForViolations:
    """Tests for scan_text_for_violations."""

    def test_flags_matching_include(self) -> None:
        """Test a matching #include produces one diagnostic at the right line."""
        content = 'int x;\n#include "detail/foo_impl.hpp"\n'
        diags = scan_text_for_violations("other.hpp", content, ["detail/foo_impl.hpp"])
        assert len(diags) == 1
        assert diags[0].line == 2
        assert diags[0].file == "other.hpp"
        assert diags[0].check_id == "enforceCppOnlyInclude"

    def test_no_violation_when_no_match(self) -> None:
        """Test no diagnostics are produced when nothing matches."""
        content = '#include "bar.hpp"\n'
        assert scan_text_for_violations("other.hpp", content, ["foo_impl.hpp"]) == []

    def test_excluded_path_is_never_flagged(self) -> None:
        """Test a filename matching exclude_paths is exempt regardless of headers."""
        content = '#include "detail/foo_impl.hpp"\n'
        diags = scan_text_for_violations(
            "wrapper/other.hpp",
            content,
            ["detail/foo_impl.hpp"],
            exclude_paths=["wrapper/"],
        )
        assert diags == []

    def test_exclude_paths_does_not_affect_other_files(self) -> None:
        """Test exclude_paths only exempts matching files."""
        content = '#include "detail/foo_impl.hpp"\n'
        diags = scan_text_for_violations(
            "other.hpp",
            content,
            ["detail/foo_impl.hpp"],
            exclude_paths=["wrapper/"],
        )
        assert len(diags) == 1


class TestExtensions:
    """Tests for the `extensions` restriction."""

    def test_only_listed_extensions_checked(self) -> None:
        """Only files with a listed extension are flagged."""
        content = '#include "units.hpp"\n'
        assert (
            scan_text_for_violations("a.hpp", content, ["units.hpp"], (), [".tpp"])
            == []
        )
        diags = scan_text_for_violations("a.tpp", content, ["units.hpp"], (), [".tpp"])
        assert len(diags) == 1

    def test_dot_optional(self) -> None:
        """A leading dot on the extension is optional."""
        content = '#include "units.hpp"\n'
        assert scan_text_for_violations("a.tpp", content, ["units.hpp"], (), ["tpp"])
