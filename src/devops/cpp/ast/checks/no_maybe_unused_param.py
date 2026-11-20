"""Flag ``[[maybe_unused]]`` on function, method and lambda parameters.

An unused parameter should be left unnamed, or keep its name only as a
comment (``const Frame & /*frame*/``), instead of carrying the attribute.
``[[maybe_unused]]`` on variables, functions and members is not affected.

Only the standard spelling (``maybe_unused`` / ``__maybe_unused__``) written
directly in the source is reported; an attribute coming from a macro
expansion is skipped.

To disable this check for a project set::

    [cpp]
    ast_check_disabled_ids = ["noMaybeUnusedParam"]
"""

from __future__ import annotations

import clang.cindex as clang

from devops.cpp.ast.base import Check, Diagnostic

_ATTRIBUTE_SPELLINGS = frozenset({"maybe_unused", "__maybe_unused__"})


def _maybe_unused_attribute(cursor: clang.Cursor) -> clang.Cursor | None:
    """Return the ``[[maybe_unused]]`` attribute child of `cursor`, if any.

    Parameters
    ----------
    cursor: clang.Cursor
        A `PARM_DECL` cursor.

    Returns
    -------
    clang.Cursor | None
        The attribute cursor, or None if the parameter does not carry
        ``[[maybe_unused]]`` spelled directly in the source.

    """
    for child in cursor.get_children():
        if not child.kind.is_attribute():
            continue
        # Macro-expanded attributes get a bogus extent spanning many tokens.
        tokens = [token.spelling for token in child.get_tokens()]
        if len(tokens) == 1 and tokens[0] in _ATTRIBUTE_SPELLINGS:
            return child
    return None


class NoMaybeUnusedParam(Check):
    """Flag parameters marked ``[[maybe_unused]]``."""

    id = "noMaybeUnusedParam"

    def visit(self, cursor: clang.Cursor, filename: str) -> list[Diagnostic]:
        """Flag the cursor if it is a parameter marked ``[[maybe_unused]]``.

        Parameters
        ----------
        cursor: clang.Cursor
            The AST node currently being visited.
        filename: str
            Path of the file being checked.

        Returns
        -------
        list[Diagnostic]
            A single diagnostic if `cursor` is a parameter carrying
            ``[[maybe_unused]]``, otherwise an empty list.

        """
        if cursor.kind != clang.CursorKind.PARM_DECL:
            return []
        attribute = _maybe_unused_attribute(cursor)
        if attribute is None:
            return []

        type_name = cursor.type.spelling
        if cursor.spelling:
            subject = f"parameter '{cursor.spelling}'"
            hint = f"'{type_name} /*{cursor.spelling}*/'"
        else:
            subject = "unnamed parameter"
            hint = f"'{type_name}'"
        loc = attribute.extent.start
        return [
            Diagnostic(
                file=filename,
                line=loc.line,
                column=loc.column,
                message=(
                    f"do not mark {subject} as [[maybe_unused]] — leave it "
                    f"unnamed or comment the name out, e.g. {hint}"
                ),
                check_id=self.id,
                severity="style",
            )
        ]
