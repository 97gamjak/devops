"""Tests for the NoClangFormatToggle AST check."""

from __future__ import annotations

import typing

import pytest

from devops.cpp.ast.checks.no_clang_format_toggle import NoClangFormatToggle
from devops.cpp.ast.engine import run_ast_checks

if typing.TYPE_CHECKING:
    from pathlib import Path

pytest.importorskip("clang.cindex")

_ARGS = ["-std=c++17"]


def _diags(code: str, path: Path) -> list[str]:
    path.write_text(code)
    return [
        d.message
        for d in run_ast_checks(path, code, _ARGS, checks=[NoClangFormatToggle()])
    ]


class TestNoClangFormatToggleFlagged:
    """Line- and block-comment clang-format toggles are flagged."""

    def test_line_comment_off_flagged(self, tmp_path: Path) -> None:
        """Test line comment off flagged."""
        code = "// clang-format off\nint x = 1;\n"
        diags = _diags(code, tmp_path / "test.cpp")
        assert len(diags) == 1
        assert "clang-format off" in diags[0]

    def test_line_comment_on_flagged(self, tmp_path: Path) -> None:
        """Test line comment on flagged."""
        code = "// clang-format off\nint x=1;\n// clang-format on\n"
        diags = _diags(code, tmp_path / "test.cpp")
        assert len(diags) == 2

    def test_block_comment_flagged(self, tmp_path: Path) -> None:
        """Test block comment flagged."""
        code = "/* clang-format off */\nint x = 1;\n"
        diags = _diags(code, tmp_path / "test.cpp")
        assert len(diags) == 1

    def test_multiple_toggles_all_flagged(self, tmp_path: Path) -> None:
        """Test multiple toggles all flagged."""
        code = (
            "// clang-format off\n"
            "int x=1;\n"
            "// clang-format on\n"
            "void f() {}\n"
            "// clang-format off\n"
            "int y=2;\n"
        )
        diags = _diags(code, tmp_path / "test.cpp")
        assert len(diags) == 3

    def test_toggle_in_header_flagged(self, tmp_path: Path) -> None:
        """Test toggle in header flagged."""
        code = "// clang-format off\nint x;\n"
        diags = _diags(code, tmp_path / "test.h")
        assert len(diags) == 1


class TestNoClangFormatToggleAllowed:
    """Ordinary comments and well-formed code are not flagged."""

    def test_plain_comment_not_flagged(self, tmp_path: Path) -> None:
        """Test plain comment not flagged."""
        code = "// just a note\nint x = 1;\n"
        assert _diags(code, tmp_path / "test.cpp") == []

    def test_no_comments_not_flagged(self, tmp_path: Path) -> None:
        """Test no comments not flagged."""
        code = "int x = 1;\nvoid f() {}\n"
        assert _diags(code, tmp_path / "test.cpp") == []

    def test_clang_format_mentioned_in_prose_not_flagged(self, tmp_path: Path) -> None:
        """Test clang-format mentioned in prose not flagged."""
        code = "// see clang-format docs for formatting rules\nint x = 1;\n"
        assert _diags(code, tmp_path / "test.cpp") == []


class TestNoClangFormatToggleCheckId:
    """The check id is correct."""

    def test_check_id(self) -> None:
        """Test check id."""
        assert NoClangFormatToggle().id == "noClangFormatToggle"
