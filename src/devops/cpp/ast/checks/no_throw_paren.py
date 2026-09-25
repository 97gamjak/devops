"""Flag throw-expressions that wrap the thrown expression in parentheses.

A ``throw(...)`` whose parentheses span the entire thrown expression is
reported — the parentheses are redundant and make the throw read like a
function call. Write the throw as ``throw ...;`` instead. This does not flag
parentheses that are only part of the thrown expression itself, such as a
constructor or function call (``throw E(1);``), only redundant parentheses
wrapping the whole expression (``throw(E(1));``, ``throw(x + 1);``). A bare
rethrow (``throw;``) is always allowed.

To disable this check for a project set::

    [cpp]
    ast_check_disabled_ids = ["noThrowParen"]
"""

from __future__ import annotations

import clang.cindex as clang

from devops.cpp.ast.base import Check, Diagnostic

# 'throw', '(', ..., ')' — the minimum tokens for a parenthesized throw.
_MIN_PAREN_THROW_TOKENS = 3


class NoThrowParen(Check):
    """Flag ``throw(...)`` where parentheses wrap the whole thrown expression."""

    id = "noThrowParen"

    def visit(self, cursor: clang.Cursor, filename: str) -> list[Diagnostic]:
        """Flag the cursor if it is a parenthesized throw-expression.

        Parameters
        ----------
        cursor: clang.Cursor
            The AST node currently being visited.
        filename: str
            Path of the file being checked.

        Returns
        -------
        list[Diagnostic]
            A single diagnostic if the cursor is a disallowed
            ``throw(...)``, otherwise an empty list.

        """
        if cursor.kind != clang.CursorKind.CXX_THROW_EXPR:
            return []

        tokens = [t.spelling for t in cursor.get_tokens()]
        if len(tokens) < _MIN_PAREN_THROW_TOKENS or tokens[1] != "(":
            return []

        if not self._wraps_whole_expression(tokens):
            return []

        loc = cursor.location
        return [
            Diagnostic(
                file=filename,
                line=loc.line,
                column=loc.column,
                message=(
                    "do not wrap the thrown expression in parentheses "
                    "('throw(...)') — write 'throw ...;' instead"
                ),
                check_id=self.id,
                severity="style",
            )
        ]

    @staticmethod
    def _wraps_whole_expression(tokens: list[str]) -> bool:
        """Check whether the '(' right after 'throw' matches the final token.

        Parameters
        ----------
        tokens: list[str]
            Token spellings of the throw-expression, starting with
            ``"throw"``; `tokens[1] == "("` is already guaranteed by the
            caller.

        Returns
        -------
        bool
            True if that opening paren's matching close paren is the last
            token, i.e. the parentheses enclose the whole expression.

        """
        depth = 0
        for i, tok in enumerate(tokens[1:], start=1):
            if tok == "(":
                depth += 1
            elif tok == ")":
                depth -= 1
                if depth == 0:
                    return i == len(tokens) - 1
        return False
