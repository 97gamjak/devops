"""Tests for the IncludeIwyuPragmaOnly AST check."""

from __future__ import annotations

import typing

import pytest

from devops.config.base import ConfigError
from devops.cpp.ast.checks.include_iwyu_pragma_only import IncludeIwyuPragmaOnly
from devops.cpp.ast.engine import run_ast_checks

if typing.TYPE_CHECKING:
    from pathlib import Path

pytest.importorskip("clang.cindex")

_ARGS = ["-std=c++17"]


def _diags(
    code: str, tmp_path: Path, check: IncludeIwyuPragmaOnly | None = None
) -> list[str]:
    (tmp_path / "foo.h").write_text("// empty header\n")
    p = tmp_path / "test.cpp"
    p.write_text(code)
    checks = [check or IncludeIwyuPragmaOnly()]
    return [d.message for d in run_ast_checks(p, code, _ARGS, checks=checks)]


class TestIncludeIwyuPragmaOnlyFlagged:
    """A trailing comment that isn't an IWYU pragma is flagged."""

    def test_plain_trailing_comment_flagged(self, tmp_path: Path) -> None:
        """Test plain trailing comment flagged."""
        code = '#include "foo.h" // needed for Foo\n'
        diags = _diags(code, tmp_path)
        assert len(diags) == 1
        assert "not an IWYU pragma" in diags[0]

    def test_block_trailing_comment_flagged(self, tmp_path: Path) -> None:
        """Test block trailing comment flagged."""
        code = '#include "foo.h" /* keep this */\n'
        diags = _diags(code, tmp_path)
        assert len(diags) == 1


class TestIncludeIwyuPragmaOnlyAllowed:
    """No trailing comment, or a valid IWYU pragma, is allowed."""

    def test_no_trailing_comment_allowed(self, tmp_path: Path) -> None:
        """Test no trailing comment allowed."""
        code = '#include "foo.h"\n'
        assert _diags(code, tmp_path) == []

    def test_iwyu_pragma_export_allowed(self, tmp_path: Path) -> None:
        """Test iwyu pragma export allowed."""
        code = '#include "foo.h" // IWYU pragma: export\n'
        assert _diags(code, tmp_path) == []

    def test_iwyu_pragma_keep_allowed(self, tmp_path: Path) -> None:
        """Test iwyu pragma keep allowed."""
        code = '#include "foo.h" // IWYU pragma: keep\n'
        assert _diags(code, tmp_path) == []

    def test_comment_on_next_line_not_flagged(self, tmp_path: Path) -> None:
        """Test comment on next line not flagged."""
        code = '#include "foo.h"\n// not a trailing comment\n'
        assert _diags(code, tmp_path) == []


class TestIncludeIwyuPragmaOnlyAllowedPragmasConfig:
    """The 'allowed_pragmas' config narrows which IWYU pragma keywords pass."""

    def test_allowed_pragma_passes(self, tmp_path: Path) -> None:
        """Test allowed pragma passes."""
        check = IncludeIwyuPragmaOnly()
        check.configure({"allowed_pragmas": ["export"]})
        code = '#include "foo.h" // IWYU pragma: export\n'
        assert _diags(code, tmp_path, check) == []

    def test_disallowed_pragma_flagged(self, tmp_path: Path) -> None:
        """Test disallowed pragma flagged."""
        check = IncludeIwyuPragmaOnly()
        check.configure({"allowed_pragmas": ["export"]})
        code = '#include "foo.h" // IWYU pragma: keep\n'
        diags = _diags(code, tmp_path, check)
        assert len(diags) == 1
        assert "keep" in diags[0]
        assert "not in the allowed list" in diags[0]

    def test_invalid_config_raises(self) -> None:
        """Test invalid config raises."""
        check = IncludeIwyuPragmaOnly()
        with pytest.raises(ConfigError):
            check.configure({"allowed_pragmas": "export"})


class TestIncludeIwyuPragmaOnlyCheckId:
    """The check id is correct."""

    def test_check_id(self) -> None:
        """Test check id."""
        assert IncludeIwyuPragmaOnly().id == "includeIwyuPragmaOnly"
