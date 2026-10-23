"""Flag use of ``class`` instead of ``typename`` for a template type parameter.

A template type parameter can be introduced with either ``class`` or
``typename`` — they are equivalent. Standardizing on ``typename`` keeps the
keyword's meaning unambiguous: ``class`` then always refers to a class
declaration, never to "some type".

To disable this check for a project set::

    [cpp]
    ast_check_disabled_ids = ["enforceTypenameOverClass"]
"""

from __future__ import annotations

import clang.cindex as clang

from devops.cpp.ast.base import Check, Diagnostic


class EnforceTypenameOverClass(Check):
    """Flag a template type parameter declared with ``class``."""

    id = "enforceTypenameOverClass"

    def visit(self, cursor: clang.Cursor, filename: str) -> list[Diagnostic]:
        """Flag the cursor if it is a ``class``-spelled template type parameter.

        Parameters
        ----------
        cursor: clang.Cursor
            The AST node currently being visited.
        filename: str
            Path of the file being checked.

        Returns
        -------
        list[Diagnostic]
            A single diagnostic if the cursor is a template type parameter
            introduced with ``class``, otherwise an empty list.

        """
        if cursor.kind != clang.CursorKind.TEMPLATE_TYPE_PARAMETER:
            return []

        tokens = [t.spelling for t in cursor.get_tokens()]
        if not tokens or tokens[0] != "class":
            return []

        loc = cursor.location
        return [
            Diagnostic(
                file=filename,
                line=loc.line,
                column=loc.column,
                message=(
                    f"use 'typename' instead of 'class' for template "
                    f"type parameter '{cursor.spelling}'"
                ),
                check_id=self.id,
                severity="style",
            )
        ]
