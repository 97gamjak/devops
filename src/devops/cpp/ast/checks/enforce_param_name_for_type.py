"""Enforce a canonical parameter name for parameters of a given type.

Maintain the TYPE_TO_NAME map below: <base type name> -> <required
parameter name>. Cv-qualifiers (const/volatile) and pointer/reference
decoration are stripped from the parameter's type before lookup, so
"const SimulationBox &", "SimulationBox *" and "SimulationBox" all
resolve to the same key and all require the same parameter name.
"""

from __future__ import annotations

import re

import clang.cindex as clang

from devops.cpp.ast.base import Check, Diagnostic

TYPE_TO_NAME = {
    "SimulationBox": "simulationBox",
    "ForceField": "forceField",
    "Optimizer": "optimizer",
    # add more as they come up
}

_QUALIFIER_RE = re.compile(r"\b(const|volatile)\b")
_DECORATION_RE = re.compile(r"[&*]")


def base_type_name(type_spelling: str) -> str:
    """Strip cv-qualifiers and pointer/reference decoration from a spelling.

    Parameters
    ----------
    type_spelling: str
        The raw type spelling as reported by libclang, e.g.
        ``"const SimulationBox &"``.

    Returns
    -------
    str
        The bare base type name, e.g. ``"SimulationBox"``.

    """
    name = _QUALIFIER_RE.sub("", type_spelling)
    name = _DECORATION_RE.sub("", name)
    return " ".join(name.split())


class EnforceParamNameForType(Check):
    """Flag parameters of a mapped type that don't use the required name."""

    id = "paramNameForType"

    def visit(self, cursor: clang.Cursor, filename: str) -> list[Diagnostic]:
        """Flag the cursor if it's a mapped-type parameter with the wrong name.

        Parameters
        ----------
        cursor: clang.Cursor
            The AST node currently being visited.
        filename: str
            Path of the file being checked.

        Returns
        -------
        list[Diagnostic]
            A single diagnostic if `cursor` is an offending parameter,
            otherwise an empty list.

        """
        if cursor.kind != clang.CursorKind.PARM_DECL:
            return []

        name = cursor.spelling
        if not name:
            # Unnamed parameter, e.g. a declaration-only header. Nothing to
            # enforce.
            return []

        type_name = base_type_name(cursor.type.spelling)
        expected = TYPE_TO_NAME.get(type_name)
        if expected is None or name == expected:
            return []

        loc = cursor.location
        return [
            Diagnostic(
                file=filename,
                line=loc.line,
                column=loc.column,
                message=(
                    f"parameter of type '{type_name}' named '{name}' "
                    f"should be named '{expected}'"
                ),
                check_id=self.id,
            )
        ]
