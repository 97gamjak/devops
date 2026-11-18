"""Enforce how parameters of certain types are passed.

Configure the per-type rules via the project TOML file:

    [cpp.ast_check_config.passByType.types]
    "molsys::SimulationBox" = { mode = "const_ref", check_getter = true }
    "Real" = "value"
    "std::string_view" = { mode = "const_ref_or_value" }

``mode`` is one of:

* ``const_ref``: the parameter must be a ``const T &``.
* ``value``: the parameter must be passed by value (``T`` or ``const T``).
* ``const_ref_or_value``: either of the above.

Non-const references, rvalue references and pointers are always flagged.
A plain string is shorthand for ``{ mode = "<string>" }``.

With ``check_getter = true`` (per type, default ``false``) the return type of
simple getters of that type (non-static, ``const`` member functions without
parameters) is checked with the same mode. Other functions' return types are
never checked.

Matching uses the base type (cv-qualifiers, references and pointers stripped),
exactly like ``paramNameForType``.
"""

from __future__ import annotations

import typing

import clang.cindex as clang

from devops.config.base import ConfigError
from devops.cpp.ast.base import Check, Diagnostic
from devops.cpp.ast.checks.enforce_param_name_for_type import declaration_type_key

_CONST_REF = "const reference"
_VALUE = "value"

_MODES: dict[str, frozenset[str]] = {
    "const_ref": frozenset({_CONST_REF}),
    "value": frozenset({_VALUE}),
    "const_ref_or_value": frozenset({_CONST_REF, _VALUE}),
}


def _passing_style(ty: clang.Type) -> str:
    """Classify how a parameter type is passed.

    Parameters
    ----------
    ty: clang.Type
        The parameter's type.

    Returns
    -------
    str
        One of ``"value"``, ``"const reference"``, ``"reference"``,
        ``"rvalue reference"`` or ``"pointer"``.

    """
    if ty.kind == clang.TypeKind.LVALUEREFERENCE:
        return _CONST_REF if ty.get_pointee().is_const_qualified() else "reference"
    if ty.kind == clang.TypeKind.RVALUEREFERENCE:
        return "rvalue reference"
    if ty.kind == clang.TypeKind.POINTER:
        return "pointer"
    return _VALUE


class _TypeRule(typing.NamedTuple):
    """Passing rule for one configured type."""

    mode: str
    check_getter: bool


class EnforcePassByType(Check):
    """Flag parameters of configured types passed in the wrong way."""

    id = "passByType"

    def __init__(self) -> None:
        """Initialise with no configured types."""
        self.types: dict[str, _TypeRule] = {}

    def configure(self, config: dict) -> None:
        """Load the per-type rules from the check's TOML config block.

        Parameters
        ----------
        config: dict
            Expected shape: ``{"types": {"TypeName": "<mode>" | {"mode":
            "<mode>", "check_getter": bool}, ...}}``.

        Raises
        ------
        ConfigError
            If ``types`` is missing/malformed, a mode is unknown, or
            ``check_getter`` is not a boolean.

        """
        if "types" not in config:
            msg = (
                "passByType: 'types' is required in "
                "[cpp.ast_check_config.passByType] but was not found"
            )
            raise ConfigError(msg)
        raw = config["types"]
        if not isinstance(raw, dict):
            msg = "passByType: 'types' must be a table of type name → rule"
            raise ConfigError(msg)

        types: dict[str, _TypeRule] = {}
        for name, value in raw.items():
            entry = {"mode": value} if isinstance(value, str) else value
            if not isinstance(entry, dict):
                msg = (
                    f"passByType: rule for '{name}' must be a mode string or "
                    "a table with 'mode' and optional 'check_getter'"
                )
                raise ConfigError(msg)
            mode = entry.get("mode")
            if mode not in _MODES:
                msg = (
                    f"passByType: invalid mode {mode!r} for '{name}', "
                    f"expected one of {sorted(_MODES)}"
                )
                raise ConfigError(msg)
            check_getter = entry.get("check_getter", False)
            if not isinstance(check_getter, bool):
                msg = f"passByType: 'check_getter' for '{name}' must be a boolean"
                raise ConfigError(msg)
            types[name.removeprefix("::")] = _TypeRule(mode, check_getter)
        self.types = types

    def _rule(self, type_name: str) -> _TypeRule | None:
        """Return the rule configured for `type_name`, if any."""
        rule = self.types.get(type_name)
        if rule is not None:
            return rule
        # Qualified keys also match with an extra leading namespace;
        # unqualified keys must match exactly.
        for key, candidate in self.types.items():
            if "::" in key and type_name.endswith(f"::{key}"):
                return candidate
        return None

    def visit(self, cursor: clang.Cursor, filename: str) -> list[Diagnostic]:
        """Flag a parameter (or simple getter return) passed/returned wrongly.

        Parameters
        ----------
        cursor: clang.Cursor
            The AST node currently being visited.
        filename: str
            Path of the file being checked.

        Returns
        -------
        list[Diagnostic]
            A single diagnostic if `cursor` is offending, otherwise an empty
            list.

        """
        if cursor.kind == clang.CursorKind.PARM_DECL:
            return self._check(
                cursor,
                cursor.type,
                filename,
                f"parameter '{cursor.spelling}'",
                "passed",
            )
        if self._is_simple_getter(cursor):
            return self._check(
                cursor,
                cursor.result_type,
                filename,
                f"getter '{cursor.spelling}'",
                "returned",
                getter=True,
            )
        return []

    @staticmethod
    def _is_simple_getter(cursor: clang.Cursor) -> bool:
        """Return whether `cursor` is a non-static const method without params."""
        return (
            cursor.kind == clang.CursorKind.CXX_METHOD
            and cursor.is_const_method()
            and not cursor.is_static_method()
            and not list(cursor.get_arguments())
            and cursor.result_type.kind != clang.TypeKind.VOID
        )

    def _check(
        self,
        cursor: clang.Cursor,
        ty: clang.Type,
        filename: str,
        subject: str,
        verb: str,
        *,
        getter: bool = False,
    ) -> list[Diagnostic]:
        """Check `ty` against the configured requirement for its base type."""
        type_name = declaration_type_key(ty)
        rule = self._rule(type_name)
        if rule is None or (getter and not rule.check_getter):
            return []

        allowed = _MODES[rule.mode]
        style = _passing_style(ty)
        if style in allowed:
            return []

        expected = " or ".join(
            f"by {s}" for s in sorted(allowed, key=lambda s: s != _CONST_REF)
        )
        loc = cursor.location
        return [
            Diagnostic(
                file=filename,
                line=loc.line,
                column=loc.column,
                message=(
                    f"{subject} of type '{type_name}' is {verb} by {style} "
                    f"but must be {verb} {expected} (mode '{rule.mode}')"
                ),
                check_id=self.id,
            )
        ]
