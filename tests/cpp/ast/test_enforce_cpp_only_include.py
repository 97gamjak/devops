"""Tests for the EnforceCppOnlyInclude AST check."""

from __future__ import annotations

import typing

import pytest

from devops.config.base import ConfigError
from devops.cpp.ast.checks.enforce_cpp_only_include import EnforceCppOnlyInclude
from devops.cpp.ast.engine import run_ast_checks

if typing.TYPE_CHECKING:
    from pathlib import Path

pytest.importorskip("clang.cindex")

_ARGS = ["-std=c++17"]


def _diags(
    code: str,
    tmp_path: Path,
    filename: str = "test.cpp",
    headers: list[str] | None = None,
    exclude_paths: list[str] | None = None,
) -> list[str]:
    (tmp_path / "detail").mkdir()
    (tmp_path / "detail" / "foo_impl.hpp").write_text("// empty header\n")
    (tmp_path / "bar.hpp").write_text("// empty header\n")
    p = tmp_path / filename
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(code)
    check = EnforceCppOnlyInclude()
    check.configure(
        {
            "libs": headers if headers is not None else ["detail/foo_impl.hpp"],
            "exclude_paths": exclude_paths or [],
        }
    )
    args = [*_ARGS, f"-I{tmp_path}"]
    return [d.message for d in run_ast_checks(p, code, args, checks=[check])]


class TestEnforceCppOnlyIncludeFlagged:
    """A configured cpp-only header included from another header is flagged."""

    def test_include_from_header_flagged(self, tmp_path: Path) -> None:
        """Test cpp-only header included from a header file is flagged."""
        code = '#include "detail/foo_impl.hpp"\n'
        diags = _diags(code, tmp_path, filename="other.hpp")
        assert len(diags) == 1
        assert "detail/foo_impl.hpp" in diags[0]

    def test_pattern_match_flagged(self, tmp_path: Path) -> None:
        """Test a glob pattern matching the basename is flagged in a header."""
        code = '#include "detail/foo_impl.hpp"\n'
        diags = _diags(code, tmp_path, filename="other.hpp", headers=["*_impl.hpp"])
        assert len(diags) == 1


class TestEnforceCppOnlyIncludeAllowed:
    """Includes from .cpp files, and unconfigured headers, are allowed."""

    def test_include_from_cpp_allowed(self, tmp_path: Path) -> None:
        """Test cpp-only header included directly from a .cpp file is allowed."""
        code = '#include "detail/foo_impl.hpp"\n'
        assert _diags(code, tmp_path, filename="test.cpp") == []

    def test_unconfigured_header_allowed(self, tmp_path: Path) -> None:
        """Test include of an unconfigured header from a header is allowed."""
        code = '#include "bar.hpp"\n'
        assert _diags(code, tmp_path, filename="other.hpp") == []

    def test_no_headers_configured_allowed(self, tmp_path: Path) -> None:
        """Test that no headers configured means nothing is flagged."""
        code = '#include "detail/foo_impl.hpp"\n'
        assert _diags(code, tmp_path, filename="other.hpp", headers=[]) == []

    def test_excluded_path_allowed(self, tmp_path: Path) -> None:
        """Test an including file matching exclude_paths is never flagged.

        Covers a header that itself wraps/defines a cpp-only header (and
        must therefore include it unconditionally), exempted via
        ``exclude_paths``.
        """
        code = '#include "detail/foo_impl.hpp"\n'
        diags = _diags(
            code,
            tmp_path,
            filename="wrapper/other.hpp",
            exclude_paths=["wrapper/"],
        )
        assert diags == []

    def test_excluded_path_does_not_affect_other_files(self, tmp_path: Path) -> None:
        """Test exclude_paths only exempts matching files, not every header."""
        code = '#include "detail/foo_impl.hpp"\n'
        diags = _diags(
            code,
            tmp_path,
            filename="other.hpp",
            exclude_paths=["wrapper/"],
        )
        assert len(diags) == 1


class TestEnforceCppOnlyIncludeConfig:
    """Configuration validation for the 'libs' key."""

    def test_invalid_config_raises(self) -> None:
        """Test invalid config raises."""
        check = EnforceCppOnlyInclude()
        with pytest.raises(ConfigError):
            check.configure({"libs": "detail/foo_impl.hpp"})

    def test_invalid_exclude_paths_raises(self) -> None:
        """Test invalid exclude_paths config raises."""
        check = EnforceCppOnlyInclude()
        with pytest.raises(ConfigError):
            check.configure(
                {"libs": ["detail/foo_impl.hpp"], "exclude_paths": "wrapper/"}
            )


class TestEnforceCppOnlyIncludeCheckId:
    """The check id is correct."""

    def test_check_id(self) -> None:
        """Test check id."""
        assert EnforceCppOnlyInclude().id == "enforceCppOnlyInclude"
