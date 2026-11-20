"""Tests for the NoMaybeUnusedParam AST check via the shared engine."""

from __future__ import annotations

import typing

import pytest

from devops.cpp.ast.checks.no_maybe_unused_param import NoMaybeUnusedParam
from devops.cpp.ast.engine import run_ast_checks

if typing.TYPE_CHECKING:
    from pathlib import Path

pytest.importorskip("clang.cindex")

_PRELUDE = "struct Frame {};\n#define UNUSED [[maybe_unused]]\n"


def _run(tmp_path: Path, code: str, name: str = "example.cpp") -> list:
    path = tmp_path / name
    content = f"{_PRELUDE}{code}\n"
    path.write_text(content)
    return run_ast_checks(path, content, ["-std=c++23"], checks=[NoMaybeUnusedParam()])


@pytest.mark.parametrize(
    "code",
    [
        "void f([[maybe_unused]] int x) {}",
        "void f(int x [[maybe_unused]]) {}",
        "void f([[maybe_unused]] const Frame &frame) {}",
        "void f([[ maybe_unused ]] int x) {}",
        "void f([[__maybe_unused__]] int x) {}",
        "void f([[maybe_unused]] int);",
        "void f(int a, [[maybe_unused]] int b) {}",
        "struct S { void m([[maybe_unused]] int p); };",
        "struct S { S([[maybe_unused]] int p) {} };",
        "auto l = []([[maybe_unused]] int p) {};",
        "template <typename T> void f([[maybe_unused]] T q) {}",
        "template <typename T> struct S { void m([[maybe_unused]] T q) {} };",
    ],
)
def test_flagged(tmp_path: Path, code: str) -> None:
    """A parameter carrying ``[[maybe_unused]]`` is flagged exactly once.

    Parameters
    ----------
    tmp_path: Path
        Temporary path for creating test files.
    code: str
        The C++ code under test.

    """
    diagnostics = _run(tmp_path, code)
    assert len(diagnostics) == 1
    assert diagnostics[0].check_id == "noMaybeUnusedParam"


@pytest.mark.parametrize(
    "code",
    [
        "void f(const Frame & /*frame*/) {}",
        "void f(int) {}",
        "void f(int x) { (void)x; }",
        "[[maybe_unused]] static int v = 0;",
        "void f() { [[maybe_unused]] int z = 1; }",
        "[[maybe_unused]] static void f(int x) { (void)x; }",
        "struct S { [[maybe_unused]] int m; };",
        "struct S { S() = default; S(const S &) = delete; };",
        "void f([[gnu::unused]] int x) {}",
        "void f(int *x [[clang::noescape]]) {}",
        "void f(UNUSED int w) {}",
    ],
)
def test_allowed(tmp_path: Path, code: str) -> None:
    """Other uses of the attribute and other attributes are not flagged.

    Parameters
    ----------
    tmp_path: Path
        Temporary path for creating test files.
    code: str
        The C++ code under test.

    """
    assert _run(tmp_path, code) == []


def test_message_and_location(tmp_path: Path) -> None:
    """The message suggests commenting the name and points at the attribute.

    Parameters
    ----------
    tmp_path: Path
        Temporary path for creating test files.

    """
    (diag,) = _run(tmp_path, "void f([[maybe_unused]] const Frame &frame) {}")
    assert "parameter 'frame'" in diag.message
    assert "'const Frame & /*frame*/'" in diag.message
    assert (diag.line, diag.column) == (3, 10)


def test_unnamed_parameter_message(tmp_path: Path) -> None:
    """An unnamed parameter is reported without a name.

    Parameters
    ----------
    tmp_path: Path
        Temporary path for creating test files.

    """
    (diag,) = _run(tmp_path, "void f([[maybe_unused]] int);")
    assert "unnamed parameter" in diag.message


def test_included_header_not_reported(tmp_path: Path) -> None:
    """Parameters declared in an included header are not reported.

    Parameters
    ----------
    tmp_path: Path
        Temporary path for creating test files.

    """
    (tmp_path / "other.hpp").write_text("void g([[maybe_unused]] int x);\n")
    diagnostics = _run(tmp_path, '#include "other.hpp"\nvoid f(int x) {}')
    assert diagnostics == []


def test_header_file_checked(tmp_path: Path) -> None:
    """A header that is itself checked is reported.

    Parameters
    ----------
    tmp_path: Path
        Temporary path for creating test files.

    """
    diagnostics = _run(tmp_path, "void g([[maybe_unused]] int x);", name="example.hpp")
    assert len(diagnostics) == 1
