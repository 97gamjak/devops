"""Tests for the NoConstValueParam AST check via the shared engine."""

from __future__ import annotations

import typing

import pytest

from devops.cpp.ast.checks.no_const_value_param import NoConstValueParam
from devops.cpp.ast.engine import run_ast_checks
from devops.cpp.ast.registry import ALL_CHECKS

if typing.TYPE_CHECKING:
    from pathlib import Path

pytest.importorskip("clang.cindex")

_PRELUDE = "struct Foo {};\nusing CInt = const int;\n#define CONST_INT const int\n"


def _run(tmp_path: Path, code: str, name: str = "example.cpp") -> list:
    cpp_file = tmp_path / name
    content = f"{_PRELUDE}{code}\n"
    cpp_file.write_text(content)
    return run_ast_checks(
        cpp_file, content, ["-std=c++23"], checks=[NoConstValueParam()]
    )


@pytest.mark.parametrize(
    "code",
    [
        "void f(const int x) {}",
        "void f(int const x) {}",
        "void f(const double x);",
        "void f(const Foo foo) {}",
        "void f(int *const p) {}",
        "void f(const int *const p) {}",
        "void f(const int x = 1) {}",
        "struct S { void m(const int x); };",
        "struct S { void m(const int x) {} };",
        "struct S { S(const int x) {} };",
        "struct S { void m(int x); };\nvoid S::m(const int x) {}",
        "template <typename T> void f(const T x) {}",
        "void f(const int x) try { (void)x; } catch (...) {}",
        "void g() { auto l = [](const int x) { return x; }; (void)l; }",
    ],
)
def test_flagged(tmp_path: Path, code: str) -> None:
    """A named by-value parameter with written top-level const is flagged.

    Parameters
    ----------
    tmp_path: Path
        Temporary path for creating test files.
    code: str
        The C++ code under test.

    """
    diagnostics = _run(tmp_path, code)
    assert len(diagnostics) == 1
    assert diagnostics[0].check_id == "noConstValueParam"


@pytest.mark.parametrize(
    "code",
    [
        "void f(int x) {}",
        "void f(const int &x) {}",
        "void f(const Foo &foo) {}",
        "void f(Foo &&foo) {}",
        "void f(const int *p) {}",
        "void f(const int x[3]) {}",
        "void f(const int) {}",
        "void f(const int);",
        "void f(CInt x) {}",
        "void f(CONST_INT x) {}",
        "#define DEF(name) void name(const int x) {}\nDEF(f)",
        "void f(const int x) = delete;",
        "struct S { void m(const int x) = delete; };",
        "struct S { S &operator=(const S &other) = default; };",
        "void (*fp)(const int x) = nullptr;",
        "using Fn = void(const int x);",
        "template <typename T> void f(const T &x) {}",
        "void g() { auto l = [](const int &x) { return x; }; (void)l; }",
        "void g() { const int x = 1; (void)x; }",
    ],
)
def test_not_flagged(tmp_path: Path, code: str) -> None:
    """References, pointers to const, unnamed, alias/macro const are allowed.

    Parameters
    ----------
    tmp_path: Path
        Temporary path for creating test files.
    code: str
        The C++ code under test.

    """
    assert _run(tmp_path, code) == []


def test_message_suggests_dropping_const(tmp_path: Path) -> None:
    """The message names the parameter, its type and the fix.

    Parameters
    ----------
    tmp_path: Path
        Temporary path for creating test files.

    """
    (diag,) = _run(tmp_path, "void f(const int x) {}")
    assert "'x'" in diag.message
    assert "'const int'" in diag.message
    assert "drop the top-level 'const'" in diag.message
    assert (diag.line, diag.column) == (4, 18)


def test_included_header_not_reported(tmp_path: Path) -> None:
    """Parameters in an included header are not reported for the main file.

    Parameters
    ----------
    tmp_path: Path
        Temporary path for creating test files.

    """
    (tmp_path / "other.hpp").write_text("inline void h(const int x) { (void)x; }\n")
    diagnostics = _run(tmp_path, '#include "other.hpp"\nvoid f(int x) {}')
    assert diagnostics == []


def test_header_is_checked(tmp_path: Path) -> None:
    """A header checked on its own reports its parameters.

    Parameters
    ----------
    tmp_path: Path
        Temporary path for creating test files.

    """
    diagnostics = _run(tmp_path, "inline void f(const int x) {}", "example.hpp")
    assert len(diagnostics) == 1


def test_registered() -> None:
    """The check is registered under its id."""
    assert any(check.id == "noConstValueParam" for check in ALL_CHECKS)
