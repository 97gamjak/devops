"""Tests for the PreferMstdCopyMoveMacros AST check via the shared engine."""

from __future__ import annotations

import typing

import pytest

from devops.config.base import ConfigError
from devops.cpp.ast.checks.prefer_mstd_copy_move_macros import (
    PreferMstdCopyMoveMacros,
)
from devops.cpp.ast.engine import run_ast_checks

if typing.TYPE_CHECKING:
    from pathlib import Path

pytest.importorskip("clang.cindex")

_MACROS = """\
#define MSTD_NO_COPY(c) c(const c &) = delete; c &operator=(const c &) = delete;
#define MSTD_NO_MOVE(c) c(c &&) = delete; c &operator=(c &&) = delete;
#define MSTD_RAII_NO_MOVE(c) MSTD_NO_COPY(c) MSTD_NO_MOVE(c)
"""


def _run(tmp_path: Path, source: str, config: dict | None = None) -> list:
    check = PreferMstdCopyMoveMacros()
    check.configure(config or {})
    cpp_file = tmp_path / "example.cpp"
    content = f"{_MACROS}{source}\n"
    cpp_file.write_text(content)
    return run_ast_checks(cpp_file, content, ["-std=c++23"], checks=[check])


@pytest.mark.parametrize(
    ("source", "count"),
    [
        ("struct X { X(const X &) = delete; };", 1),
        ("struct X { X &operator=(const X &) = delete; };", 1),
        ("struct X { X(X &&) = delete; };", 1),
        ("struct X { X &operator=(X &&) = delete; };", 1),
        (
            (
                "struct X { X(const X &) = delete; X &operator=(const X &) = delete;"
                " X(X &&) = delete; X &operator=(X &&) = delete; };"
            ),
            4,
        ),
        ('struct X { X(const X &) = delete("no"); };', 1),
        ("template <typename T> struct X { X(const X &) = delete; };", 1),
        ("struct X { MSTD_NO_COPY(X) };", 0),
        ("struct X { MSTD_NO_MOVE(X) };", 0),
        ("struct X { MSTD_RAII_NO_MOVE(X) };", 0),
        ("template <typename T> struct X { MSTD_RAII_NO_MOVE(X) };", 0),
        ("struct X { X(const X &) = default; X(X &&) = default; };", 0),
        ("struct X { X &operator=(const X &) = default; };", 0),
        ("struct X { X(int) = delete; void f() = delete; };", 0),
        ("struct X { X(const X &); X &operator=(X &&); };", 0),
        ("struct X { X(const X &) {} };", 0),
        (
            (
                "template <typename T> struct X { template <typename U>"
                " X(const X<U> &) = delete; };"
            ),
            0,
        ),
        ("void f(int) = delete;", 0),
    ],
)
def test_detection(tmp_path: Path, source: str, count: int) -> None:
    """Only hand-written deleted copy/move members are flagged.

    Parameters
    ----------
    tmp_path: Path
        Temporary path for creating test files.
    source: str
        The C++ code under test.
    count: int
        The expected number of diagnostics.

    """
    diagnostics = _run(tmp_path, source)
    assert len(diagnostics) == count
    assert all(d.check_id == "preferMstdCopyMoveMacros" for d in diagnostics)


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("struct Foo { Foo(const Foo &) = delete; };", "MSTD_NO_COPY(Foo)"),
        ("struct Foo { Foo &operator=(Foo &&) = delete; };", "MSTD_NO_MOVE(Foo)"),
        (
            "template <typename T> struct Foo { Foo(Foo &&) = delete; };",
            "MSTD_NO_MOVE(Foo)",
        ),
    ],
)
def test_message_suggests_macro(tmp_path: Path, source: str, expected: str) -> None:
    """The message names the member and the macro to use instead.

    Parameters
    ----------
    tmp_path: Path
        Temporary path for creating test files.
    source: str
        The C++ code under test.
    expected: str
        The macro call expected in the message.

    """
    (diag,) = _run(tmp_path, source)
    assert expected in diag.message
    assert "'Foo'" in diag.message


def test_configured_macro_names(tmp_path: Path) -> None:
    """Configured macro names replace the mstd defaults in the message.

    Parameters
    ----------
    tmp_path: Path
        Temporary path for creating test files.

    """
    diagnostics = _run(
        tmp_path,
        "struct X { X(const X &) = delete; X(X &&) = delete; };",
        {"copy_macro": "MY_NO_COPY", "move_macro": "MY_NO_MOVE"},
    )
    messages = [d.message for d in diagnostics]
    assert any("MY_NO_COPY(X)" in m for m in messages)
    assert any("MY_NO_MOVE(X)" in m for m in messages)


def test_included_header_not_flagged(tmp_path: Path) -> None:
    """Members in an included header are not reported for the main file.

    Parameters
    ----------
    tmp_path: Path
        Temporary path for creating test files.

    """
    (tmp_path / "other.hpp").write_text("struct Y { Y(const Y &) = delete; };\n")
    diagnostics = _run(tmp_path, '#include "other.hpp"\nstruct X {};')
    assert diagnostics == []


def test_header_is_checked(tmp_path: Path) -> None:
    """A header checked on its own reports its hand-written members.

    Parameters
    ----------
    tmp_path: Path
        Temporary path for creating test files.

    """
    header = tmp_path / "example.hpp"
    content = "struct X { X(X &&) = delete; };\n"
    header.write_text(content)
    diagnostics = run_ast_checks(
        header, content, ["-std=c++23"], checks=[PreferMstdCopyMoveMacros()]
    )
    assert len(diagnostics) == 1
    assert diagnostics[0].line == 1


@pytest.mark.parametrize(
    "config",
    [
        {"copy_macro": 1},
        {"copy_macro": ""},
        {"move_macro": "NO MOVE"},
        {"move_macro": ["MSTD_NO_MOVE"]},
    ],
)
def test_invalid_config_raises(config: dict) -> None:
    """Malformed macro names raise ConfigError.

    Parameters
    ----------
    config: dict
        The invalid configuration.

    """
    with pytest.raises(ConfigError):
        PreferMstdCopyMoveMacros().configure(config)
