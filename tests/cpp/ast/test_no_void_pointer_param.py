"""Tests for the NoVoidPointerParam AST check via the shared engine."""

from __future__ import annotations

import typing

import pytest

from devops.cpp.ast.checks.no_void_pointer_param import NoVoidPointerParam
from devops.cpp.ast.engine import run_ast_checks

if typing.TYPE_CHECKING:
    from pathlib import Path

pytest.importorskip("clang.cindex")


def _run(tmp_path: Path, code: str, name: str = "example.cpp") -> list:
    source = tmp_path / name
    source.write_text(code)
    return run_ast_checks(source, code, ["-std=c++23"], checks=[NoVoidPointerParam()])


@pytest.mark.parametrize(
    "code",
    [
        "void f(void *p);",
        "void f(const void *p) {}",
        "void f(const volatile void *p);",
        "void f(void **p);",
        "void f(const void *const *p);",
        "void f(void *&p);",
        "void f(void *);",
        "using Handle = void *; void f(Handle h);",
        "typedef const void *CHandle; void f(CHandle h);",
        "namespace ns { void f(void *p); }",
        "template <typename T> void f(T t, void *p);",
        "struct S { void f(void *p); };",
        "struct S { static void f(void *p); };",
        "class S { public: S(void *p); };",
        "class S { protected: void f(void *p); };",
        "class S { public: template <typename T> void f(void *p); };",
        "template <typename T> struct S { S(void *p); };",
        "struct S { friend void f(S s, void *p); };",
        "namespace { struct A {}; } namespace ns { void f(void *p); }",
        "#define VOIDP void *\nvoid f(VOIDP p);",
        "#define API\nAPI void f(void *p);",
    ],
)
def test_flagged(tmp_path: Path, code: str) -> None:
    """Public ``void *`` parameters are flagged exactly once.

    Parameters
    ----------
    tmp_path: Path
        Temporary path for creating test files.
    code: str
        The C++ code under test.

    """
    diagnostics = _run(tmp_path, code)
    assert len(diagnostics) == 1
    assert diagnostics[0].check_id == "noVoidPointerParam"


@pytest.mark.parametrize(
    "code",
    [
        "void f(int *p);",
        "void f(char *p);",
        "void f(void (*cb)(void *));",
        "using Cb = void (*)(void *); void f(Cb cb);",
        "template <typename T> void f(T *p);",
        "template <typename T> void f(T p);",
        "static void f(void *p) {}",
        "namespace { void f(void *p) {} }",
        "namespace { struct S { void f(void *p); }; }",
        'extern "C" void f(void *p);',
        'extern "C" { void f(void *p); }',
        "class S { void f(void *p); };",
        "class S { S(void *p); };",
        "struct S { private: void f(void *p); };",
        "class S { public: S(void *p) = delete; };",
        "struct S { void f(void *p) = delete; };",
        "void f(void *p) = delete;",
        "void g() { struct L { void f(void *p) {} }; }",
        "void g() { auto l = [](void *p) {}; }",
        "#define DECL(name) void name(void *p);\nDECL(f)",
        "#define GEN void generated(void *p);\nGEN",
    ],
)
def test_allowed(tmp_path: Path, code: str) -> None:
    """Non-public, internal, deleted, override and macro cases are allowed.

    Parameters
    ----------
    tmp_path: Path
        Temporary path for creating test files.
    code: str
        The C++ code under test.

    """
    diagnostics = [
        d for d in _run(tmp_path, code) if d.check_id == "noVoidPointerParam"
    ]
    assert diagnostics == []


def test_override_reported_on_base_only(tmp_path: Path) -> None:
    """Only the base declaration is flagged, not the override.

    Parameters
    ----------
    tmp_path: Path
        Temporary path for creating test files.

    """
    code = (
        "struct B { virtual void f(void *p); };\n"
        "struct D : B { void f(void *p) override; };\n"
    )
    diagnostics = _run(tmp_path, code)
    assert [d.line for d in diagnostics] == [1]


def test_out_of_line_definition_reported_once(tmp_path: Path) -> None:
    """A method declared and defined out of line is reported at its declaration.

    Parameters
    ----------
    tmp_path: Path
        Temporary path for creating test files.

    """
    code = "struct S {\n  void f(void *p);\n};\nvoid S::f(void *p) {}\n"
    diagnostics = _run(tmp_path, code)
    assert [d.line for d in diagnostics] == [2]


def test_every_offending_parameter_is_reported(tmp_path: Path) -> None:
    """Each ``void *`` parameter gets its own diagnostic with its location.

    Parameters
    ----------
    tmp_path: Path
        Temporary path for creating test files.

    """
    diagnostics = _run(tmp_path, "void f(void *a, int b, const void *c);")
    assert [d.column for d in diagnostics] == [14, 36]
    assert "'a'" in diagnostics[0].message
    assert "'f'" in diagnostics[0].message
    assert "'const void *'" in diagnostics[1].message


def test_header_is_checked(tmp_path: Path) -> None:
    """Headers are checked like source files.

    Parameters
    ----------
    tmp_path: Path
        Temporary path for creating test files.

    """
    diagnostics = _run(
        tmp_path, "#pragma once\nstruct S {\n  void f(void *p);\n};\n", "s.hpp"
    )
    assert [d.line for d in diagnostics] == [3]


def test_included_header_is_not_reported(tmp_path: Path) -> None:
    """Functions from an included header are not reported for the main file.

    Parameters
    ----------
    tmp_path: Path
        Temporary path for creating test files.

    """
    (tmp_path / "api.hpp").write_text("#pragma once\nvoid g(void *p);\n")
    code = '#include "api.hpp"\nvoid f(int *p);\n'
    diagnostics = _run(tmp_path, code)
    assert diagnostics == []
