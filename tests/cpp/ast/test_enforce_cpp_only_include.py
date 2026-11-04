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
) -> list[str]:
    (tmp_path / "detail").mkdir()
    (tmp_path / "detail" / "foo_impl.hpp").write_text("// empty header\n")
    (tmp_path / "bar.hpp").write_text("// empty header\n")
    p = tmp_path / filename
    p.write_text(code)
    check = EnforceCppOnlyInclude()
    check.configure(
        {"headers": headers if headers is not None else ["detail/foo_impl.hpp"]}
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


class TestEnforceCppOnlyIncludeConfig:
    """Configuration validation for the 'headers' key."""

    def test_invalid_config_raises(self) -> None:
        """Test invalid config raises."""
        check = EnforceCppOnlyInclude()
        with pytest.raises(ConfigError):
            check.configure({"headers": "detail/foo_impl.hpp"})


class TestEnforceCppOnlyIncludeCheckId:
    """The check id is correct."""

    def test_check_id(self) -> None:
        """Test check id."""
        assert EnforceCppOnlyInclude().id == "enforceCppOnlyInclude"
