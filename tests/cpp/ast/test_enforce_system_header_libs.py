"""Tests for the EnforceSystemHeaderLibs AST check."""

from __future__ import annotations

import typing

import pytest

from devops.config.base import ConfigError
from devops.cpp.ast.checks.enforce_system_header_libs import EnforceSystemHeaderLibs
from devops.cpp.ast.engine import run_ast_checks

if typing.TYPE_CHECKING:
    from pathlib import Path

pytest.importorskip("clang.cindex")

_ARGS = ["-std=c++17"]


def _diags(code: str, tmp_path: Path, libs: list[str] | None = None) -> list[str]:
    (tmp_path / "mstd").mkdir()
    (tmp_path / "mstd" / "foo.hpp").write_text("// empty header\n")
    (tmp_path / "bar.hpp").write_text("// empty header\n")
    p = tmp_path / "test.cpp"
    p.write_text(code)
    check = EnforceSystemHeaderLibs()
    check.configure({"libs": libs if libs is not None else ["mstd"]})
    args = [*_ARGS, f"-I{tmp_path}"]
    return [d.message for d in run_ast_checks(p, code, args, checks=[check])]


class TestEnforceSystemHeaderLibsFlagged:
    """A quoted #include of a configured library is flagged."""

    def test_quoted_include_flagged(self, tmp_path: Path) -> None:
        """Test quoted include of a configured lib is flagged."""
        code = '#include "mstd/foo.hpp"\n'
        diags = _diags(code, tmp_path)
        assert len(diags) == 1
        assert "mstd/foo.hpp" in diags[0]
        assert "<mstd/foo.hpp>" in diags[0]


class TestEnforceSystemHeaderLibsAllowed:
    """Angle-bracket includes, and includes of unconfigured libs, are allowed."""

    def test_angle_include_allowed(self, tmp_path: Path) -> None:
        """Test angle-bracket include of a configured lib is allowed."""
        code = "#include <mstd/foo.hpp>\n"
        assert _diags(code, tmp_path) == []

    def test_unconfigured_lib_allowed(self, tmp_path: Path) -> None:
        """Test quoted include of an unconfigured lib is allowed."""
        code = '#include "bar.hpp"\n'
        assert _diags(code, tmp_path) == []

    def test_no_libs_configured_allowed(self, tmp_path: Path) -> None:
        """Test that no libs configured means nothing is flagged."""
        code = '#include "mstd/foo.hpp"\n'
        assert _diags(code, tmp_path, libs=[]) == []


class TestEnforceSystemHeaderLibsConfig:
    """Configuration validation for the 'libs' key."""

    def test_invalid_config_raises(self) -> None:
        """Test invalid config raises."""
        check = EnforceSystemHeaderLibs()
        with pytest.raises(ConfigError):
            check.configure({"libs": "mstd"})


class TestEnforceSystemHeaderLibsCheckId:
    """The check id is correct."""

    def test_check_id(self) -> None:
        """Test check id."""
        assert EnforceSystemHeaderLibs().id == "enforceSystemHeaderLibs"
