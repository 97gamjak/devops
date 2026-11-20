"""Tests for the NoInClassMemberDefinition AST check via the shared engine."""

from __future__ import annotations

import typing

import pytest

from devops.cpp.ast.checks.no_in_class_member_definition import (
    NoInClassMemberDefinition,
)
from devops.cpp.ast.engine import run_ast_checks
from devops.cpp.ast.registry import ALL_CHECKS

if typing.TYPE_CHECKING:
    from pathlib import Path

    from devops.cpp.ast.base import Diagnostic

pytest.importorskip("clang.cindex")


def _run(tmp_path: Path, code: str, name: str = "example.cpp") -> list[Diagnostic]:
    path = tmp_path / name
    path.write_text(code)
    return run_ast_checks(
        path, code, ["-std=c++23"], checks=[NoInClassMemberDefinition()]
    )


@pytest.mark.parametrize(
    "code",
    [
        "struct S { void f(); };\nvoid S::f() {}",
        "struct S { S(); ~S(); };\nS::S() {}\nS::~S() {}",
        "struct S { S() = default; ~S() = default; };",
        "struct S { S(const S &) = delete; S &operator=(S &&) = delete; };",
        "struct S { virtual void f() = 0; virtual ~S() = default; };",
        "struct S { static int g(); };\nint S::g() { return 1; }",
        (
            "template <typename T> struct S { T f(); };\n"
            "template <typename T> T S<T>::f() { return T{}; }"
        ),
        (
            "struct S { template <typename T> T f(); };\n"
            "template <typename T> T S::f() { return T{}; }"
        ),
        "struct S { friend bool operator==(S, S) { return true; } };",
        "void g() { auto l = [](int x) { return x; }; (void)l; }",
        "struct S { int x = [] { return 1; }(); };",
        "void g() { struct L { int f() { return 1; } }; (void)L{}.f(); }",
        ("struct S { void f(); };\nvoid S::f() { struct L { void h() {} }; L{}.h(); }"),
        "struct { int f() { return 1; } } unnamed;",
        "struct S { struct { void f() {} } member; };",
        "#define DEF struct M { int f() { return 1; } };\nDEF",
        "#define GETTER(n) int n() const { return 1; }\nstruct S { GETTER(get) };",
    ],
)
def test_allowed(tmp_path: Path, code: str) -> None:
    """Declarations, special forms, local/unnamed classes and macros pass.

    Parameters
    ----------
    tmp_path: Path
        Temporary path for creating test files.
    code: str
        The C++ source under test.

    """
    assert _run(tmp_path, code) == []


@pytest.mark.parametrize(
    ("code", "subject"),
    [
        ("struct S { void f() {} };", "member function 'f'"),
        ("class C { int f() const { return 1; } };", "member function 'f'"),
        ("struct S { static int g() { return 1; } };", "member function 'g'"),
        ("struct S { S() {} };", "constructor 'S'"),
        ("struct S { ~S() {} };", "destructor '~S'"),
        (
            "struct S { bool operator==(const S &) const { return true; } };",
            "member function 'operator=='",
        ),
        (
            "struct S { explicit operator bool() const { return true; } };",
            "conversion function 'operator bool'",
        ),
        ("struct S { virtual void f() {} };", "member function 'f'"),
        ("struct S { constexpr int f() const { return 1; } };", "member function 'f'"),
        ("union U { int f() { return 1; } int i; };", "member function 'f'"),
        (
            "template <typename T> struct S { T f() { return T{}; } };",
            "member function 'f'",
        ),
        (
            "struct S { template <typename T> T f() { return T{}; } };",
            "member function 'f'",
        ),
        (
            (
                "template <typename T, typename U> struct S {};\n"
                "template <typename T> struct S<T, int> { void f() {} };"
            ),
            "member function 'f'",
        ),
        ("struct O { struct I { void f() {} }; };", "member function 'f'"),
        (
            "#define VALUE 1\nstruct S { int f() { return VALUE; } };",
            "member function 'f'",
        ),
    ],
)
def test_flagged(tmp_path: Path, code: str, subject: str) -> None:
    """Every member function with an in-class body is flagged once.

    Parameters
    ----------
    tmp_path: Path
        Temporary path for creating test files.
    code: str
        The C++ source under test.
    subject: str
        Expected subject at the start of the message.

    """
    diagnostics = _run(tmp_path, code)
    assert len(diagnostics) == 1
    assert diagnostics[0].check_id == "noInClassMemberDefinition"
    assert diagnostics[0].message.startswith(subject)


def test_message_and_location(tmp_path: Path) -> None:
    """The diagnostic names the class and points at the member's name.

    Parameters
    ----------
    tmp_path: Path
        Temporary path for creating test files.

    """
    (diag,) = _run(tmp_path, "struct Box {\n    void resize() {}\n};\n")
    assert (diag.line, diag.column) == (2, 10)
    assert "class 'Box'" in diag.message
    assert "define it outside" in diag.message


def test_header_flagged(tmp_path: Path) -> None:
    """Headers are checked like source files.

    Parameters
    ----------
    tmp_path: Path
        Temporary path for creating test files.

    """
    code = "#pragma once\nstruct S { void f() {} void g(); };\n"
    assert len(_run(tmp_path, code, name="example.hpp")) == 1


def test_included_header_not_reported(tmp_path: Path) -> None:
    """In-class bodies in an included header are not reported for the includer.

    Parameters
    ----------
    tmp_path: Path
        Temporary path for creating test files.

    """
    (tmp_path / "other.hpp").write_text("#pragma once\nstruct S { void f() {} };\n")
    code = '#include "other.hpp"\nvoid g() { S{}.f(); }\n'
    assert _run(tmp_path, code) == []


def test_registered() -> None:
    """The check is part of the default check list."""
    assert any(check.id == "noInClassMemberDefinition" for check in ALL_CHECKS)
