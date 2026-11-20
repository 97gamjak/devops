"""Limit the size of anonymous namespaces.

Everything inside an anonymous namespace has internal linkage, so it cannot
be reached from a unit test. A few small helpers are fine; anything bigger
belongs in a named (e.g. ``detail``) namespace where it can be tested.

An anonymous namespace is flagged if it

* defines any class, struct or union (including class templates), or
* has more than ``max_declarations`` top-level declarations. Functions,
  function templates, variables and type aliases/typedefs count; a function
  declared and later defined in the same namespace counts once.

Each ``namespace { ... }`` block is checked on its own. Declarations pulled
in from other files (e.g. an ``#include`` inside the block) are ignored.

Configure the limit via the project TOML file::

    [cpp.ast_check_config.maxAnonymousNamespaceSize]
    max_declarations = 3
"""

from __future__ import annotations

import clang.cindex as clang

from devops.config.base import ConfigError
from devops.cpp.ast.base import Check, Diagnostic

_DEFAULT_MAX_DECLARATIONS = 3

_CLASS_KINDS = frozenset(
    {
        clang.CursorKind.CLASS_DECL,
        clang.CursorKind.STRUCT_DECL,
        clang.CursorKind.UNION_DECL,
        clang.CursorKind.CLASS_TEMPLATE,
        clang.CursorKind.CLASS_TEMPLATE_PARTIAL_SPECIALIZATION,
    }
)

_DECLARATION_KINDS = frozenset(
    {
        clang.CursorKind.FUNCTION_DECL,
        clang.CursorKind.FUNCTION_TEMPLATE,
        clang.CursorKind.VAR_DECL,
        clang.CursorKind.TYPEDEF_DECL,
        clang.CursorKind.TYPE_ALIAS_DECL,
        clang.CursorKind.TYPE_ALIAS_TEMPLATE_DECL,
    }
)


def _same_file(cursor: clang.Cursor, other: clang.Cursor) -> bool:
    """Return whether both cursors are located in the same file."""
    file = cursor.location.file
    other_file = other.location.file
    return file is not None and other_file is not None and file.name == other_file.name


def _key(cursor: clang.Cursor) -> str | tuple[int, int]:
    """Return an identity for `cursor` shared by its redeclarations."""
    return cursor.get_usr() or (cursor.location.line, cursor.location.column)


class MaxAnonymousNamespaceSize(Check):
    """Flag anonymous namespaces holding a class or too many declarations."""

    id = "maxAnonymousNamespaceSize"

    def __init__(self) -> None:
        """Initialise with the default declaration limit."""
        self.max_declarations = _DEFAULT_MAX_DECLARATIONS

    def configure(self, config: dict) -> None:
        """Load ``max_declarations`` from the check's TOML config block.

        Parameters
        ----------
        config: dict
            Expected shape: ``{"max_declarations": int}``; the key is
            optional.

        Raises
        ------
        ConfigError
            If ``max_declarations`` is not a non-negative integer.

        """
        value = config.get("max_declarations", _DEFAULT_MAX_DECLARATIONS)
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            msg = (
                f"{self.id}: 'max_declarations' must be a non-negative "
                f"integer, got {value!r}"
            )
            raise ConfigError(msg)
        self.max_declarations = value

    def visit(self, cursor: clang.Cursor, filename: str) -> list[Diagnostic]:
        """Flag `cursor` if it is an anonymous namespace that is too large.

        Parameters
        ----------
        cursor: clang.Cursor
            The AST node currently being visited.
        filename: str
            Path of the file being checked.

        Returns
        -------
        list[Diagnostic]
            A single diagnostic at the namespace's opening location if it is
            too large, otherwise an empty list.

        """
        if cursor.kind != clang.CursorKind.NAMESPACE or cursor.spelling:
            return []

        classes: list[str] = []
        declarations: set[str | tuple[int, int]] = set()
        for child in cursor.get_children():
            if not _same_file(child, cursor):
                continue
            if child.kind in _CLASS_KINDS and child.is_definition():
                classes.append(child.spelling or "<unnamed>")
            elif child.kind in _DECLARATION_KINDS:
                declarations.add(_key(child))

        too_many = len(declarations) > self.max_declarations
        if not classes and not too_many:
            return []

        problems = []
        if classes:
            names = ", ".join(f"'{name}'" for name in classes)
            problems.append(f"defines {len(classes)} class(es) ({names}; limit 0)")
        if too_many:
            problems.append(
                f"has {len(declarations)} top-level declarations "
                f"(limit {self.max_declarations})"
            )
        # An anonymous namespace's location is its brace, not the keyword.
        loc = cursor.extent.start
        return [
            Diagnostic(
                file=filename,
                line=loc.line,
                column=loc.column,
                message=(
                    f"anonymous namespace {' and '.join(problems)}; move the "
                    "code to a named namespace so it can be tested"
                ),
                check_id=self.id,
            )
        ]
