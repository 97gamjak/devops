"""Flag ``using enum`` declarations at namespace/global scope.

Any ``using enum X;`` (C++20) that appears directly inside a translation unit
or a named/anonymous namespace is reported as an error, since it injects every
enumerator of ``X`` into the enclosing scope. The same declaration inside a
function or class body is allowed because its effect is confined to that scope.

This is separate from `noGlobalUsing` so the two can be toggled independently.

To disable this check for a project set::

    [cpp]
    ast_check_disabled_ids = ["noGlobalUsingEnum"]

To restrict the check to (or exempt) specific enums, use the per-check table.
Names are matched exactly against the qualified enum name as written in the
source; a leading ``::`` is ignored::

    [cpp.ast_check_config.noGlobalUsingEnum]
    enabled_names = ["molsys::HybridZone"]
    disabled_names = ["molsys::Legacy"]
"""

from __future__ import annotations

import clang.cindex as clang

from devops.cpp.ast.base import Diagnostic
from devops.cpp.ast.checks.name_filtered import NameFilteredCheck

_GLOBAL_PARENT_KINDS = frozenset(
    (
        clang.CursorKind.TRANSLATION_UNIT,
        clang.CursorKind.NAMESPACE,
    )
)


class NoGlobalUsingEnum(NameFilteredCheck):
    """Flag ``using enum X;`` at global/namespace scope.

    The libclang Python bindings have no cursor kind for using-enum
    declarations: they surface as a childless, non-definition ``ENUM_DECL``.
    They are told apart from real enum declarations (and forward
    declarations) by their first token being ``using`` rather than ``enum``.
    """

    id = "noGlobalUsingEnum"

    def visit(self, cursor: clang.Cursor, filename: str) -> list[Diagnostic]:
        """Flag the cursor if it is a global-scope ``using enum`` declaration.

        Parameters
        ----------
        cursor: clang.Cursor
            The AST node currently being visited.
        filename: str
            Path of the file being checked.

        Returns
        -------
        list[Diagnostic]
            A single diagnostic if the cursor is a disallowed ``using enum``,
            otherwise an empty list.

        """
        if cursor.kind != clang.CursorKind.ENUM_DECL or cursor.is_definition():
            return []

        parent = cursor.semantic_parent
        if parent is None or parent.kind not in _GLOBAL_PARENT_KINDS:
            return []

        tokens = [t.spelling for t in cursor.get_tokens()]
        if tokens[:2] != ["using", "enum"]:
            return []

        name = "".join(t for t in tokens[2:] if t != ";") or cursor.spelling
        if not self._is_selected(name):
            return []

        loc = cursor.location
        return [
            Diagnostic(
                file=filename,
                line=loc.line,
                column=loc.column,
                message=(
                    f"do not use 'using enum {name.removeprefix('::')}' at "
                    "namespace/global scope — confine it to a function body"
                ),
                check_id=self.id,
                severity="style",
            )
        ]
