"""Tests for the NoNewInGtestSetup AST check."""

from __future__ import annotations

import typing

import pytest

from devops.cpp.ast.checks.no_new_in_gtest_setup import NoNewInGtestSetup
from devops.cpp.ast.engine import run_ast_checks

if typing.TYPE_CHECKING:
    from pathlib import Path

pytest.importorskip("clang.cindex")

_CHECK = [NoNewInGtestSetup()]
_ARGS = ["-std=c++17"]


def _diags(code: str, tmp_path: Path) -> list[str]:
    p = tmp_path / "test.cpp"
    p.write_text(code)
    return [d.message for d in run_ast_checks(p, code, _ARGS, checks=_CHECK)]


class TestNewInSetupFlagged:
    """`new` in a recognised setup hook is flagged."""

    def test_new_in_setup_flagged(self, tmp_path: Path) -> None:
        """Test new in SetUp flagged."""
        code = "struct FooTest {\n  void SetUp() {\n    int* p = new int(1);\n  }\n};\n"
        diags = _diags(code, tmp_path)
        assert len(diags) == 1
        assert "'new'" in diags[0]
        assert "SetUp()" in diags[0]

    def test_new_array_in_setup_flagged(self, tmp_path: Path) -> None:
        """Test array new in SetUp flagged."""
        code = "struct FooTest {\n  void SetUp() {\n    int* p = new int[3];\n  }\n};\n"
        diags = _diags(code, tmp_path)
        assert len(diags) == 1

    def test_new_in_setup_test_suite_flagged(self, tmp_path: Path) -> None:
        """Test new in SetUpTestSuite flagged."""
        code = (
            "struct FooTest {\n"
            "  static void SetUpTestSuite() {\n"
            "    shared_ = new int(1);\n"
            "  }\n"
            "  static int* shared_;\n"
            "};\n"
        )
        diags = _diags(code, tmp_path)
        assert len(diags) == 1
        assert "SetUpTestSuite()" in diags[0]

    def test_new_in_setup_test_case_flagged(self, tmp_path: Path) -> None:
        """Test new in SetUpTestCase flagged."""
        code = (
            "struct FooTest {\n"
            "  static void SetUpTestCase() {\n"
            "    shared_ = new int(1);\n"
            "  }\n"
            "  static int* shared_;\n"
            "};\n"
        )
        diags = _diags(code, tmp_path)
        assert len(diags) == 1
        assert "SetUpTestCase()" in diags[0]

    def test_multiple_news_all_flagged(self, tmp_path: Path) -> None:
        """Test multiple news all flagged."""
        code = (
            "struct FooTest {\n"
            "  void SetUp() {\n"
            "    int* a = new int(1);\n"
            "    int* b = new int(2);\n"
            "  }\n"
            "};\n"
        )
        assert len(_diags(code, tmp_path)) == 2

    def test_new_in_nested_lambda_flagged(self, tmp_path: Path) -> None:
        """Test new inside a lambda defined in SetUp is still flagged."""
        code = (
            "struct FooTest {\n"
            "  void SetUp() {\n"
            "    auto f = []() { return new int(1); };\n"
            "    f();\n"
            "  }\n"
            "};\n"
        )
        assert len(_diags(code, tmp_path)) == 1


class TestNewElsewhereAllowed:
    """`new` outside a recognised setup hook is not flagged."""

    def test_new_in_tear_down_allowed(self, tmp_path: Path) -> None:
        """Test new in TearDown allowed."""
        code = (
            "struct FooTest {\n  void TearDown() {\n    int* p = new int(1);\n  }\n};\n"
        )
        assert _diags(code, tmp_path) == []

    def test_new_in_unrelated_method_allowed(self, tmp_path: Path) -> None:
        """Test new in an unrelated method allowed."""
        code = "struct S {\n  void Init() {\n    int* p = new int(1);\n  }\n};\n"
        assert _diags(code, tmp_path) == []

    def test_new_in_free_function_named_setup_allowed(self, tmp_path: Path) -> None:
        """Test new in a free function (not a method) named SetUp allowed."""
        code = "void SetUp() {\n  int* p = new int(1);\n}\n"
        assert _diags(code, tmp_path) == []

    def test_setup_declaration_without_body_allowed(self, tmp_path: Path) -> None:
        """Test a SetUp declaration with no body is not flagged."""
        code = "struct Base {\n  virtual void SetUp() = 0;\n};\n"
        assert _diags(code, tmp_path) == []

    def test_clean_setup_produces_no_diagnostics(self, tmp_path: Path) -> None:
        """Test clean file produces no diagnostics."""
        code = (
            "struct FooTest {\n"
            "  void SetUp() {\n"
            "    ptr_ = std::make_unique<int>(1);\n"
            "  }\n"
            "};\n"
        )
        assert _diags(code, tmp_path) == []


class TestNoNewInGtestSetupCheckId:
    """The check id is correct and the check is selectable."""

    def test_check_id(self) -> None:
        """Test check id."""
        assert NoNewInGtestSetup().id == "noNewInGtestSetup"
