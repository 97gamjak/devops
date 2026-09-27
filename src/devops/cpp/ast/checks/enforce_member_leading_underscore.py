"""Enforce a leading underscore on private and protected member variables.

Any non-static or static data member declared under a ``private:`` or
``protected:`` access specifier must have a name starting with ``_``
(e.g. ``_count``, ``_isValid``). Public members are never flagged, since
they are part of the class's external interface and not the concern of
this check.

To disable this check for a project set::

    [cpp]
    ast_check_disabled_ids = ["memberLeadingUnderscore"]
"""

from __future__ import annotations

import clang.cindex as clang

from devops.cpp.ast.base import Check, Diagnostic

# Cursor kinds of a record whose direct data members this check inspects.
_RECORD_KINDS = frozenset(
    (
        clang.CursorKind.CLASS_DECL,
        clang.CursorKind.STRUCT_DECL,
        clang.CursorKind.UNION_DECL,
        clang.CursorKind.CLASS_TEMPLATE,
        clang.CursorKind.CLASS_TEMPLATE_PARTIAL_SPECIALIZATION,
    )
)

# FIELD_DECL covers non-static data members; a static data member is a
# VAR_DECL whose semantic parent is the record itself (filtered via
# _RECORD_KINDS below, since VAR_DECL also covers ordinary local/global
# variables).
_MEMBER_KINDS = frozenset((clang.CursorKind.FIELD_DECL, clang.CursorKind.VAR_DECL))

_RESTRICTED_ACCESS = frozenset(
    (clang.AccessSpecifier.PRIVATE, clang.AccessSpecifier.PROTECTED)
)


class EnforceMemberLeadingUnderscore(Check):
    """Flag private/protected member variables without a leading underscore."""

    id = "memberLeadingUnderscore"

    def visit(self, cursor: clang.Cursor, filename: str) -> list[Diagnostic]:
        """Flag the cursor if it's a restricted member missing a leading underscore.

        Parameters
        ----------
        cursor: clang.Cursor
            The AST node currently being visited.
        filename: str
            Path of the file being checked.

        Returns
        -------
        list[Diagnostic]
            A single diagnostic if `cursor` is an offending member variable,
            otherwise an empty list.

        """
        if cursor.kind not in _MEMBER_KINDS:
            return []

        if cursor.access_specifier not in _RESTRICTED_ACCESS:
            return []

        parent = cursor.semantic_parent
        if parent is None or parent.kind not in _RECORD_KINDS:
            return []

        name = cursor.spelling
        if not name or name.startswith("_"):
            return []

        access = (
            "private"
            if cursor.access_specifier == clang.AccessSpecifier.PRIVATE
            else "protected"
        )
        loc = cursor.location
        return [
            Diagnostic(
                file=filename,
                line=loc.line,
                column=loc.column,
                message=(
                    f"{access} member variable '{name}' should start with a "
                    f"leading underscore ('_{name}')"
                ),
                check_id=self.id,
                severity="style",
            )
        ]
