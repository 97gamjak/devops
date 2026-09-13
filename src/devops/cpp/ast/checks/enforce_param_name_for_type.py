"""Enforce a canonical parameter name for parameters of a given type.

Configure the type→name mapping via the project TOML file:

    [cpp.ast_check_config.paramNameForType]
    type_to_name = { SimulationBox = "simulationBox", ForceField = "forceField" }

Cv-qualifiers (const/volatile) and pointer/reference decoration are
stripped from the parameter's type before lookup, so
"const SimulationBox &", "SimulationBox *" and "SimulationBox" all
resolve to the same key and all require the same parameter name.
"""

from __future__ import annotations

import re

import clang.cindex as clang

from devops.config.base import ConfigError
from devops.cpp.ast.base import Check, Diagnostic
from devops.logger import cpp_check_logger

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
    """Flag parameters of a mapped type that don't use the required name.

    The type→name mapping is empty by default and must be populated via
    ``configure()`` (driven by ``cpp.ast_check_config.paramNameForType``
    in the project TOML file).
    """

    id = "paramNameForType"

    def __init__(self) -> None:
        """Initialise with an empty type-to-name mapping."""
        self.type_to_name: dict[str, str] = {}
        self._seen_type_names: set[str] = set()

    def configure(self, config: dict) -> None:
        """Load the type→name mapping from the check's TOML config block.

        Parameters
        ----------
        config: dict
            Expected shape: ``{"type_to_name": {"TypeName": "paramName", ...}}``.

        Raises
        ------
        ConfigError
            If ``type_to_name`` is present but is not a ``dict[str, str]``.

        """
        raw = config.get("type_to_name", {})
        if not isinstance(raw, dict) or not all(
            isinstance(k, str) and isinstance(v, str) for k, v in raw.items()
        ):
            msg = (
                "paramNameForType: 'type_to_name' must be a table of "
                "string → string mappings"
            )
            raise ConfigError(msg)
        self.type_to_name = dict(raw)
        self._seen_type_names = set()

    def global_finalize(self) -> None:
        """Warn about configured types that were never seen as parameter types.

        If a configured type name was not encountered in any `PARM_DECL` node
        across all checked files, it likely means the name in the TOML is
        wrong (e.g. missing namespace prefix).

        """
        for type_name in self.type_to_name:
            if type_name not in self._seen_type_names:
                cpp_check_logger.warning(
                    f"paramNameForType: configured type '{type_name}' was never "
                    "seen as a parameter type across all checked files — is the "
                    "qualified name correct?"
                )

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
        self._seen_type_names.add(type_name)
        expected = self.type_to_name.get(type_name)

        loc = cursor.location
        if expected is not None or "::" in type_name or (type_name and type_name[0].isupper()):
            cpp_check_logger.debug(
                f"paramNameForType: saw PARM_DECL '{name}' of type '{type_name}' at "
                f"{filename}:{loc.line}:{loc.column} "
                f"(raw spelling: '{cursor.type.spelling}')"
                + (f" [configured, expected '{expected}']" if expected else " [not configured]")
            )

        if expected is None:
            return []

        if name == expected:
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
