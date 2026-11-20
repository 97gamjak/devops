"""Tests for the MaxAnonymousNamespaceSize AST check via the shared engine."""

from __future__ import annotations

import typing

import pytest

from devops.config.base import ConfigError
from devops.cpp.ast.checks.max_anonymous_namespace_size import (
    MaxAnonymousNamespaceSize,
)
from devops.cpp.ast.engine import run_ast_checks

if typing.TYPE_CHECKING:
    from pathlib import Path

pytest.importorskip("clang.cindex")


def _run(
    tmp_path: Path,
    content: str,
    config: dict | None = None,
    extra_args: list[str] | None = None,
) -> list:
    check = MaxAnonymousNamespaceSize()
    check.configure(config or {})
    cpp_file = tmp_path / "example.cpp"
    cpp_file.write_text(content)
    args = ["-std=c++23", *(extra_args or [])]
    return run_ast_checks(cpp_file, content, args, checks=[check])


@pytest.mark.parametrize(
    ("content", "flagged"),
    [
        ("namespace {}", False),
        ("namespace { int a(); int b(); int c(); }", False),
        ("namespace { int a(); int b(); int c(); int d(); }", True),
        ("namespace { int a = 1; double b; const char *c = nullptr; int d; }", True),
        ("namespace { using A = int; typedef int B; using C = A; using D = B; }", True),
        ("namespace { struct S {}; }", True),
        ("namespace { class C {}; }", True),
        ("namespace { union U { int i; float f; }; }", True),
        ("namespace { template <typename T> struct S {}; }", True),
        ("namespace { struct S; class C; }", False),
        ("namespace n { struct S {}; int a(); int b(); int c(); int d(); }", False),
        ("namespace n { namespace { struct S {}; } }", True),
        ("struct S {}; int a(); int b(); int c(); int d();", False),
        # A function declared and later defined counts once.
        ("namespace { int a(); int b(); int c(); int a() { return 1; } }", False),
        # Templates count once, like ordinary functions.
        (
            (
                "namespace { template <typename T> T a(T x) { return x; } "
                "template <typename T> using V = T; int b(); }"
            ),
            False,
        ),
        (
            (
                "namespace { template <typename T> T a(T x) { return x; } "
                "template <typename T> using V = T; int b(); int c(); }"
            ),
            True,
        ),
        # Deleted functions are still declarations.
        ("namespace { void a() = delete; int b(); int c(); int d(); }", True),
        # Members of a class are not top-level declarations; the class is.
        (
            (
                "namespace { struct S { S() = default; S(const S &) = delete; "
                "int a(); int b(); int c(); int d(); }; }"
            ),
            True,
        ),
        # Lambdas are variables and count as one declaration each.
        ("namespace { auto f = [](int x) { return x; }; int a(); int b(); }", False),
        (
            (
                "namespace { static_assert(true); using std_size = decltype(sizeof 0); "
                "int a(); int b(); }"
            ),
            False,
        ),
    ],
)
def test_flagging(tmp_path: Path, content: str, *, flagged: bool) -> None:
    """Diagnostics are raised exactly for too large anonymous namespaces.

    Parameters
    ----------
    tmp_path: Path
        Temporary path for creating test files.
    content: str
        The C++ source under test.
    flagged: bool
        Whether a diagnostic is expected.

    """
    diagnostics = _run(tmp_path, content)
    assert len(diagnostics) == int(flagged)
    if flagged:
        assert diagnostics[0].check_id == "maxAnonymousNamespaceSize"


@pytest.mark.parametrize(
    ("max_declarations", "count", "flagged"),
    [(0, 0, False), (0, 1, True), (5, 5, False), (5, 6, True)],
)
def test_configured_limit(
    tmp_path: Path, max_declarations: int, count: int, *, flagged: bool
) -> None:
    """The configured limit is the largest allowed number of declarations.

    Parameters
    ----------
    tmp_path: Path
        Temporary path for creating test files.
    max_declarations: int
        The configured limit.
    count: int
        Number of declarations in the anonymous namespace.
    flagged: bool
        Whether a diagnostic is expected.

    """
    body = " ".join(f"int f{i}();" for i in range(count))
    diagnostics = _run(
        tmp_path,
        f"namespace {{ {body} }}",
        {"max_declarations": max_declarations},
    )
    assert len(diagnostics) == int(flagged)


def test_message_and_location(tmp_path: Path) -> None:
    """One diagnostic at the namespace keyword names classes, count and limit.

    Parameters
    ----------
    tmp_path: Path
        Temporary path for creating test files.

    """
    content = (
        "int x();\n"
        "  namespace {\n"
        "struct S {};\n"
        "int a(); int b(); int c(); int d();\n"
        "}\n"
    )
    (diag,) = _run(tmp_path, content)
    assert (diag.line, diag.column) == (2, 3)
    assert "defines 1 class(es) ('S'; limit 0)" in diag.message
    assert "has 4 top-level declarations (limit 3)" in diag.message


def test_each_block_reported_separately(tmp_path: Path) -> None:
    """Every ``namespace { ... }`` block is checked on its own.

    Parameters
    ----------
    tmp_path: Path
        Temporary path for creating test files.

    """
    content = (
        "namespace { int a(); int b(); }\n"
        "namespace { int c(); int d(); }\n"
        "namespace { struct S {}; }\n"
        "namespace { struct T {}; }\n"
    )
    diagnostics = _run(tmp_path, content)
    assert [d.line for d in diagnostics] == [3, 4]


def test_macro_expansions_are_counted(tmp_path: Path) -> None:
    """Declarations produced by a macro are counted like written ones.

    Parameters
    ----------
    tmp_path: Path
        Temporary path for creating test files.

    """
    content = (
        "#define DECLARE(name) int name##1(); int name##2();\n"
        "namespace { DECLARE(a) DECLARE(b) }\n"
    )
    (diag,) = _run(tmp_path, content)
    assert "has 4 top-level declarations" in diag.message


def test_included_declarations_are_ignored(tmp_path: Path) -> None:
    """Declarations from a header included inside the block do not count.

    Parameters
    ----------
    tmp_path: Path
        Temporary path for creating test files.

    """
    (tmp_path / "inc.hpp").write_text(
        "struct S {};\nint a(); int b(); int c(); int d();\n"
    )
    content = 'namespace {\n#include "inc.hpp"\nint e();\n}\n'
    assert _run(tmp_path, content, extra_args=[f"-I{tmp_path}"]) == []


def test_system_header_namespaces_are_ignored(tmp_path: Path) -> None:
    """Anonymous namespaces in (system) headers are not reported.

    Parameters
    ----------
    tmp_path: Path
        Temporary path for creating test files.

    """
    sys_dir = tmp_path / "sys"
    sys_dir.mkdir()
    (sys_dir / "lib.hpp").write_text("namespace { struct S {}; }\n")
    content = "#include <lib.hpp>\nint main() { return 0; }\n"
    assert _run(tmp_path, content, extra_args=[f"-isystem{sys_dir}"]) == []


def test_default_limit() -> None:
    """Without configuration the limit is three declarations."""
    assert MaxAnonymousNamespaceSize().max_declarations == 3


@pytest.mark.parametrize(
    "config",
    [
        {"max_declarations": -1},
        {"max_declarations": "3"},
        {"max_declarations": 2.5},
        {"max_declarations": True},
    ],
)
def test_invalid_config(config: dict) -> None:
    """Malformed configuration raises ConfigError.

    Parameters
    ----------
    config: dict
        The invalid configuration.

    """
    with pytest.raises(ConfigError, match="max_declarations"):
        MaxAnonymousNamespaceSize().configure(config)
