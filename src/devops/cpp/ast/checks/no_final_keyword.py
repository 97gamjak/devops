"""Flag use of the ``final`` specifier on classes, structs, and methods.

``final`` prevents a class from being derived from, or a virtual method from
being overridden further down the hierarchy. Banning it keeps the class
hierarchy open for extension (e.g. test doubles, future subclasses) instead
of locking it down at the point of declaration.

To disable this check for a project set::

    [cpp]
    ast_check_disabled_ids = ["noFinalKeyword"]
"""

from __future__ import annotations

import clang.cindex as clang

from devops.cpp.ast.base import Check, Diagnostic

_CLASS_LIKE_KINDS = (clang.CursorKind.CLASS_DECL, clang.CursorKind.STRUCT_DECL)


class NoFinalKeyword(Check):
    """Flag ``final`` on a class/struct declaration or a virtual method."""

    id = "noFinalKeyword"

    def visit(self, cursor: clang.Cursor, filename: str) -> list[Diagnostic]:
        """Flag the cursor if it declares something marked ``final``.

        Parameters
        ----------
        cursor: clang.Cursor
            The AST node currently being visited.
        filename: str
            Path of the file being checked.

        Returns
        -------
        list[Diagnostic]
            A single diagnostic if the cursor is a disallowed ``final``
            class/struct/method declaration, otherwise an empty list.

        """
        if cursor.kind in _CLASS_LIKE_KINDS:
            if not self._class_has_final(cursor):
                return []
            subject = f"{cursor.kind.name.split('_')[0].lower()} '{cursor.spelling}'"
        elif cursor.kind == clang.CursorKind.CXX_METHOD:
            if not self._method_has_final(cursor):
                return []
            subject = f"method '{cursor.spelling}'"
        else:
            return []

        loc = cursor.location
        return [
            Diagnostic(
                file=filename,
                line=loc.line,
                column=loc.column,
                message=(f"do not mark {subject} as 'final' — remove the specifier"),
                check_id=self.id,
                severity="style",
            )
        ]

    @staticmethod
    def _class_has_final(cursor: clang.Cursor) -> bool:
        """Check whether a class/struct's head carries the 'final' specifier.

        Parameters
        ----------
        cursor: clang.Cursor
            A `CLASS_DECL`/`STRUCT_DECL` cursor.

        Returns
        -------
        bool
            True if 'final' appears between the class name and the
            base-clause/body, i.e. as the class-virt-specifier.

        """
        tokens = [t.spelling for t in cursor.get_tokens()]
        try:
            name_index = tokens.index(cursor.spelling)
        except ValueError:
            return False

        for spelling in tokens[name_index + 1 :]:
            if spelling in ("{", ":", ";"):
                return False
            if spelling == "final":
                return True
        return False

    @staticmethod
    def _method_has_final(cursor: clang.Cursor) -> bool:
        """Check whether a method's trailing specifiers carry 'final'.

        Parameters
        ----------
        cursor: clang.Cursor
            A `CXX_METHOD` cursor.

        Returns
        -------
        bool
            True if 'final' appears after the closing ')' of the parameter
            list, i.e. as the member-function virt-specifier (excludes any
            parameter merely named "final", which lives inside the parens).

        """
        depth = 0
        seen_params = False
        for token in cursor.get_tokens():
            spelling = token.spelling
            if spelling == "(":
                depth += 1
                continue
            if spelling == ")":
                depth -= 1
                if depth == 0:
                    seen_params = True
                continue
            if not seen_params:
                continue
            if spelling in ("{", ";"):
                return False
            if spelling == "final":
                return True
        return False
