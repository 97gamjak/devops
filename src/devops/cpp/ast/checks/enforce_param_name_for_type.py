"""Enforce a canonical parameter name for parameters of a given type.

Configure the type→name mapping via the project TOML file:

    [cpp.ast_check_config.paramNameForType]
    type_to_name = { SimulationBox = "simulationBox", ForceField = "forceField" }

Cv-qualifiers (const/volatile) and pointer/reference decoration are
stripped from the parameter's type before lookup, so
``"const SimulationBox &"``, ``"SimulationBox *"`` and ``"SimulationBox"``
all resolve to the same key and all require the same parameter name.
"""

from __future__ import annotations

import re

import clang.cindex as clang

from devops.config.base import ConfigError
from devops.cpp.ast.base import Check, Diagnostic
from devops.logger import cpp_check_logger

_QUALIFIER_RE = re.compile(r"\b(const|volatile|class|struct|enum|union)\b")
_DECORATION_RE = re.compile(r"[&*]")

_REF_OR_PTR_KINDS = frozenset(
    (
        clang.TypeKind.LVALUEREFERENCE,
        clang.TypeKind.RVALUEREFERENCE,
        clang.TypeKind.POINTER,
    )
)


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


def declaration_type_key(cursor_type: clang.Type) -> str:
    """Return the fully-qualified base type name for a parameter type.

    Peels reference/pointer layers, then walks the declaration's semantic
    parent chain to build the canonical qualified name (e.g.
    ``"molsys::SimulationBox"``).  This approach is immune to ``using
    namespace`` directives and to libclang's varying ``class``/``struct``
    spelling prefixes in canonical type strings.

    Falls back to ``base_type_name`` on the raw spelling for primitive
    types that have no declaration cursor (``int``, ``float``, etc.).

    Parameters
    ----------
    cursor_type: clang.Type
        The type of the ``PARM_DECL`` cursor.

    Returns
    -------
    str
        The fully-qualified base type name.

    """
    ty = cursor_type
    while ty.kind in _REF_OR_PTR_KINDS:
        ty = ty.get_pointee()

    # Use get_declaration() directly (not via get_canonical()) so that typedef/
    # alias chains that go through unexpected namespaces (e.g. std-internal
    # aliases) don't pollute the qualified name we build.
    decl = ty.get_declaration()
    if decl.kind == clang.CursorKind.NO_DECL_FOUND:
        # Primitive type — fall back to string stripping on the raw spelling.
        return base_type_name(cursor_type.spelling)

    parts: list[str] = []
    c = decl
    while c and c.kind != clang.CursorKind.TRANSLATION_UNIT:
        if c.spelling:
            parts.append(c.spelling)
        c = c.semantic_parent
    return "::".join(reversed(parts))


class EnforceParamNameForType(Check):
    """Flag parameters of a mapped type that don't use the required name.

    The type→name mapping is empty by default and must be populated via
    ``configure()`` (driven by ``cpp.ast_check_config.paramNameForType``
    in the project TOML file).
    """

    id = "paramNameForType"

    def __init__(self) -> None:
        """Initialise with an empty type-to-name mapping."""
        self.type_to_name: dict[str, list[str]] = {}
        self._seen_type_names: set[str] = set()
        self.unseen_type_is_error: bool = False

    def configure(self, config: dict) -> None:
        """Load the type→name mapping from the check's TOML config block.

        Parameters
        ----------
        config: dict
            Expected shape: ``{"type_to_name": {"TypeName": "paramName", ...},
            "unseen_type_is_error": false}``.
            Values may be a single string or a list of strings to allow
            multiple valid parameter names for the same type.

        Raises
        ------
        ConfigError
            If ``type_to_name`` is missing or has an invalid shape.

        """
        if "type_to_name" not in config:
            msg = (
                "paramNameForType: 'type_to_name' is required in "
                "[cpp.ast_check_config.paramNameForType] but was not found — "
                "check your TOML formatting (the key must appear before any "
                "subsequent [section] header)"
            )
            raise ConfigError(msg)
        raw = config["type_to_name"]

        def _valid_value(v: object) -> bool:
            if isinstance(v, str):
                return True
            return isinstance(v, list) and all(isinstance(s, str) for s in v)

        if not isinstance(raw, dict) or not all(
            isinstance(k, str) and _valid_value(v) for k, v in raw.items()
        ):
            msg = (
                "paramNameForType: 'type_to_name' must be a table of "
                "string → string (or string → list[string]) mappings"
            )
            raise ConfigError(msg)
        self.type_to_name = {
            k.removeprefix("::"): ([v] if isinstance(v, str) else list(v))
            for k, v in raw.items()
        }
        self._seen_type_names = set()
        self.unseen_type_is_error = bool(config.get("unseen_type_is_error", False))

    def global_finalize(self) -> bool:
        """Warn (or error) about configured types never seen as parameter types.

        If a configured type name was not encountered in any `PARM_DECL` node
        across all checked files, it likely means the name in the TOML is
        wrong (e.g. missing namespace prefix).

        Returns
        -------
        bool
            False if any unseen types were found and ``unseen_type_is_error``
            is enabled, True otherwise.

        """
        cpp_check_logger.debug(
            f"paramNameForType: global_finalize — configured keys: {list(self.type_to_name)}, "
            f"seen types: {sorted(self._seen_type_names)}"
        )
        passed = True
        for type_name in self.type_to_name:
            seen = type_name in self._seen_type_names or (
                "::" in type_name
                and any(t.endswith(f"::{type_name}") for t in self._seen_type_names)
            )
            if not seen:
                if self.unseen_type_is_error:
                    cpp_check_logger.error(
                        f"paramNameForType: configured type '{type_name}' was never "
                        "seen as a parameter type across all checked files — is the "
                        "qualified name correct?"
                    )
                    passed = False
                else:
                    cpp_check_logger.warning(
                        f"paramNameForType: configured type '{type_name}' was never "
                        "seen as a parameter type across all checked files — is the "
                        "qualified name correct?"
                    )
        return passed

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

        type_name = declaration_type_key(cursor.type)
        self._seen_type_names.add(type_name)
        # Match by exact key or by suffix (e.g. "molsys::SimulationBox" matches
        # "std::molsys::SimulationBox" when the namespace is wrapped in another).
        matched_key = type_name
        expected = self.type_to_name.get(type_name)
        if expected is None:
            for key, value in self.type_to_name.items():
                # Suffix match only for qualified keys (e.g. "molsys::Foo" matches
                # "std::molsys::Foo"). Unqualified keys must be exact matches only.
                if "::" in key and type_name.endswith(f"::{key}"):
                    expected = value
                    matched_key = key
                    break

        loc = cursor.location
        cpp_check_logger.debug(
            f"paramNameForType: saw PARM_DECL '{name}' of type '{type_name}' at "
            f"{filename}:{loc.line}:{loc.column} "
            f"(raw spelling: '{cursor.type.spelling}', kind: {cursor.type.kind})"
            + (f" [configured, expected one of {expected}]" if expected else " [not configured]")  # noqa: E501
        )

        if expected is None:
            return []

        if name in expected:
            return []

        loc = cursor.location
        allowed = " or ".join(f"'{n}'" for n in expected)
        return [
            Diagnostic(
                file=filename,
                line=loc.line,
                column=loc.column,
                message=(
                    f"parameter of type '{matched_key}' named '{name}' "
                    f"should be named {allowed}"
                ),
                check_id=self.id,
            )
        ]
