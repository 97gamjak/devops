"""Tests for the NoDeleteInGtestTeardown AST check."""

from __future__ import annotations

import typing

import pytest

from devops.cpp.ast.checks.no_delete_in_gtest_teardown import NoDeleteInGtestTeardown
from devops.cpp.ast.engine import run_ast_checks

if typing.TYPE_CHECKING:
    from pathlib import Path

pytest.importorskip("clang.cindex")

_CHECK = [NoDeleteInGtestTeardown()]
_ARGS = ["-std=c++17"]


def _diags(code: str, tmp_path: Path) -> list[str]:
    p = tmp_path / "test.cpp"
    p.write_text(code)
    return [d.message for d in run_ast_checks(p, code, _ARGS, checks=_CHECK)]


class TestDeleteInTeardownFlagged:
    """`delete`/`delete[]` in a recognised teardown hook is flagged."""

    def test_delete_in_teardown_flagged(self, tmp_path: Path) -> None:
        """Test delete in TearDown flagged."""
        code = (
            "struct FooTest {\n"
            "  void TearDown() {\n"
            "    int* p = new int(1);\n"
            "    delete p;\n"
            "  }\n"
            "};\n"
        )
        diags = _diags(code, tmp_path)
        assert len(diags) == 1
        assert "'delete'" in diags[0]
        assert "TearDown()" in diags[0]

    def test_delete_array_in_teardown_flagged(self, tmp_path: Path) -> None:
        """Test delete[] in TearDown flagged."""
        code = (
            "struct FooTest {\n"
            "  void TearDown() {\n"
            "    int* p = new int[3];\n"
            "    delete[] p;\n"
            "  }\n"
            "};\n"
        )
        diags = _diags(code, tmp_path)
        assert len(diags) == 1
        assert "'delete[]'" in diags[0]

    def test_delete_in_teardown_test_suite_flagged(self, tmp_path: Path) -> None:
        """Test delete in TearDownTestSuite flagged."""
        code = (
            "struct FooTest {\n"
            "  static void TearDownTestSuite() {\n"
            "    delete shared_;\n"
            "  }\n"
            "  static int* shared_;\n"
            "};\n"
        )
        diags = _diags(code, tmp_path)
        assert len(diags) == 1
        assert "TearDownTestSuite()" in diags[0]

    def test_delete_in_teardown_test_case_flagged(self, tmp_path: Path) -> None:
        """Test delete in TearDownTestCase flagged."""
        code = (
            "struct FooTest {\n"
            "  static void TearDownTestCase() {\n"
            "    delete shared_;\n"
            "  }\n"
            "  static int* shared_;\n"
            "};\n"
        )
        diags = _diags(code, tmp_path)
        assert len(diags) == 1
        assert "TearDownTestCase()" in diags[0]

    def test_multiple_deletes_all_flagged(self, tmp_path: Path) -> None:
        """Test multiple deletes all flagged."""
        code = (
            "struct FooTest {\n"
            "  void TearDown() {\n"
            "    int* a = nullptr;\n"
            "    int* b = nullptr;\n"
            "    delete a;\n"
            "    delete b;\n"
            "  }\n"
            "};\n"
        )
        assert len(_diags(code, tmp_path)) == 2

    def test_delete_in_nested_lambda_flagged(self, tmp_path: Path) -> None:
        """Test delete inside a lambda defined in TearDown is still flagged."""
        code = (
            "struct FooTest {\n"
            "  void TearDown() {\n"
            "    auto f = [](int* p) { delete p; };\n"
            "    f(nullptr);\n"
            "  }\n"
            "};\n"
        )
        assert len(_diags(code, tmp_path)) == 1


class TestDeleteElsewhereAllowed:
    """`delete` outside a recognised teardown hook is not flagged."""

    def test_delete_in_set_up_allowed(self, tmp_path: Path) -> None:
        """Test delete in SetUp allowed."""
        code = "struct FooTest {\n  void SetUp() {\n    delete p;\n  }\n};\n"
        assert _diags(code, tmp_path) == []

    def test_delete_in_unrelated_method_allowed(self, tmp_path: Path) -> None:
        """Test delete in an unrelated method allowed."""
        code = "struct S {\n  void Cleanup() {\n    delete p;\n  }\n};\n"
        assert _diags(code, tmp_path) == []

    def test_delete_in_free_function_named_teardown_allowed(
        self, tmp_path: Path
    ) -> None:
        """Test delete in a free function (not a method) named TearDown allowed."""
        code = "void TearDown() {\n  int* p = nullptr;\n  delete p;\n}\n"
        assert _diags(code, tmp_path) == []

    def test_teardown_declaration_without_body_allowed(self, tmp_path: Path) -> None:
        """Test a TearDown declaration with no body is not flagged."""
        code = "struct Base {\n  virtual void TearDown() = 0;\n};\n"
        assert _diags(code, tmp_path) == []

    def test_clean_teardown_produces_no_diagnostics(self, tmp_path: Path) -> None:
        """Test clean file produces no diagnostics."""
        code = "struct FooTest {\n  void TearDown() {\n    ptr_.reset();\n  }\n};\n"
        assert _diags(code, tmp_path) == []


class TestNoDeleteInGtestTeardownCheckId:
    """The check id is correct and the check is selectable."""

    def test_check_id(self) -> None:
        """Test check id."""
        assert NoDeleteInGtestTeardown().id == "noDeleteInGtestTeardown"
