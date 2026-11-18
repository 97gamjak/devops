"""Tests for the EnforcePassByType AST check via the shared engine."""

from __future__ import annotations

import typing

import pytest

from devops.config.base import ConfigError
from devops.cpp.ast.checks.enforce_pass_by_type import EnforcePassByType
from devops.cpp.ast.engine import run_ast_checks

if typing.TYPE_CHECKING:
    from pathlib import Path

pytest.importorskip("clang.cindex")


def _run(tmp_path: Path, config: dict, signature: str) -> list:
    check = EnforcePassByType()
    check.configure(config)
    cpp_file = tmp_path / "example.cpp"
    content = f"struct Foo {{}};\nnamespace ns {{ struct Bar {{}}; }}\n{signature}\n"
    cpp_file.write_text(content)
    return run_ast_checks(cpp_file, content, ["-std=c++23"], checks=[check])


@pytest.mark.parametrize(
    ("config", "signature", "flagged"),
    [
        ({"types": {"Foo": "const_ref"}}, "void f(const Foo &a) {}", False),
        ({"types": {"Foo": "const_ref"}}, "void f(Foo a) {}", True),
        ({"types": {"Foo": "const_ref"}}, "void f(Foo &a) {}", True),
        ({"types": {"Foo": "const_ref"}}, "void f(Foo &&a) {}", True),
        ({"types": {"Foo": "const_ref"}}, "void f(const Foo *a) {}", True),
        ({"types": {"Foo": "value"}}, "void f(Foo a) {}", False),
        ({"types": {"Foo": "value"}}, "void f(const Foo a) {}", False),
        ({"types": {"Foo": "value"}}, "void f(const Foo &a) {}", True),
        ({"types": {"Foo": "const_ref_or_value"}}, "void f(Foo a) {}", False),
        ({"types": {"Foo": "const_ref_or_value"}}, "void f(const Foo &a) {}", False),
        ({"types": {"Foo": "const_ref_or_value"}}, "void f(Foo &a) {}", True),
        ({"types": {"ns::Bar": "const_ref"}}, "void f(ns::Bar a) {}", True),
        ({"types": {"::ns::Bar": "const_ref"}}, "void f(const ns::Bar &a) {}", False),
        ({"types": {"Other": "const_ref"}}, "void f(Foo a) {}", False),
        ({"types": {}}, "void f(Foo &a) {}", False),
    ],
)
def test_passing_style(
    tmp_path: Path, config: dict, signature: str, *, flagged: bool
) -> None:
    """Diagnostics are raised exactly when the passing style is disallowed.

    Parameters
    ----------
    tmp_path: Path
        Temporary path for creating test files.
    config: dict
        The check configuration.
    signature: str
        The C++ function definition under test.
    flagged: bool
        Whether a diagnostic is expected.

    """
    diagnostics = _run(tmp_path, config, signature)
    assert len(diagnostics) == int(flagged)
    if flagged:
        assert diagnostics[0].check_id == "passByType"


def test_message_names_expected_style(tmp_path: Path) -> None:
    """The message states the actual and required passing style.

    Parameters
    ----------
    tmp_path: Path
        Temporary path for creating test files.

    """
    (diag,) = _run(tmp_path, {"types": {"Foo": "const_ref"}}, "void f(Foo a) {}")
    assert "'a'" in diag.message
    assert "passed by value" in diag.message
    assert "by const reference" in diag.message


@pytest.mark.parametrize(
    "config",
    [
        {},
        {"types": ["Foo"]},
        {"types": {"Foo": "bogus"}},
        {"types": {"Foo": 1}},
        {"types": {"Foo": {}}},
        {"types": {"Foo": {"mode": "value", "check_getter": "yes"}}},
    ],
)
def test_invalid_config_raises(config: dict) -> None:
    """Malformed configuration raises ConfigError.

    Parameters
    ----------
    config: dict
        The invalid configuration.

    """
    with pytest.raises(ConfigError):
        EnforcePassByType().configure(config)


_GETTER_CFG = {"Foo": {"mode": "const_ref", "check_getter": True}}


@pytest.mark.parametrize(
    ("types", "member", "flagged"),
    [
        (_GETTER_CFG, "const Foo &get() const;", False),
        (_GETTER_CFG, "Foo get() const;", True),
        (_GETTER_CFG, "Foo &get() const;", True),
        (_GETTER_CFG, "const Foo *get() const;", True),
        ({"Foo": {"mode": "value", "check_getter": True}}, "Foo get() const;", False),
        (
            {"Foo": {"mode": "value", "check_getter": True}},
            "const Foo &get() const;",
            True,
        ),
        # Non-getters are never checked.
        (_GETTER_CFG, "Foo make();", False),
        (_GETTER_CFG, "Foo get(int i) const;", False),
        (_GETTER_CFG, "static Foo get();", False),
        # check_getter is per type and off by default.
        ({"Foo": "const_ref"}, "Foo get() const;", False),
        ({"Foo": {"mode": "const_ref"}}, "Foo get() const;", False),
    ],
)
def test_getter_return_types(
    tmp_path: Path, types: dict, member: str, *, flagged: bool
) -> None:
    """Simple getters are checked only for types with check_getter = true.

    Parameters
    ----------
    tmp_path: Path
        Temporary path for creating test files.
    types: dict
        The per-type rules.
    member: str
        Member function declaration inside a class.
    flagged: bool
        Whether a diagnostic is expected.

    """
    diagnostics = _run(tmp_path, {"types": types}, f"struct S {{ {member} }};")
    assert len(diagnostics) == int(flagged)
    if flagged:
        assert "getter 'get'" in diagnostics[0].message


def test_getter_flag_is_per_type(tmp_path: Path) -> None:
    """Only the type with check_getter enabled has its getter checked.

    Parameters
    ----------
    tmp_path: Path
        Temporary path for creating test files.

    """
    types = {
        "Foo": {"mode": "const_ref", "check_getter": True},
        "ns::Bar": {"mode": "const_ref"},
    }
    diagnostics = _run(
        tmp_path,
        {"types": types},
        "struct S { Foo a() const; ns::Bar b() const; };",
    )
    assert len(diagnostics) == 1
    assert "getter 'a'" in diagnostics[0].message
