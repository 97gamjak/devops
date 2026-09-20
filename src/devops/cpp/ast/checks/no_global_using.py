"""Flag 'using namespace' directives and using declarations at namespace/global scope.

Any ``using namespace X;`` or ``using X::Y;`` that appears directly inside a
translation unit or a named/anonymous namespace is reported as an error.
Identical constructs inside a function, lambda, or class body are silently
allowed because their effect is confined to that scope.

To disable this check for a project set::

    [cpp]
    ast_check_disabled_ids = ["noGlobalUsing"]
"""

from __future__ import annotations

import clang.cindex as clang

from devops.cpp.ast.base import Check, Diagnostic

# Parent cursor kinds that indicate a using-statement is at global/namespace scope.
_GLOBAL_PARENT_KINDS = frozenset(
    (
        clang.CursorKind.TRANSLATION_UNIT,
        clang.CursorKind.NAMESPACE,
    )
)

# The two cursor kinds that represent using-statements in C++.
_USING_KINDS = frozenset(
    (
        clang.CursorKind.USING_DIRECTIVE,    # using namespace X;
        clang.CursorKind.USING_DECLARATION,  # using X::Y;
    )
)


class NoGlobalUsing(Check):
    """Flag using-namespace directives and using declarations at global/namespace scope.

    Only using-statements whose immediate semantic parent is a translation
    unit or a namespace are flagged.  Those inside functions, lambdas, or
    class bodies are ignored.
    """

    id = "noGlobalUsing"

    def visit(self, cursor: clang.Cursor, filename: str) -> list[Diagnostic]:
        """Flag the cursor if it is a global-scope using-statement.

        Parameters
        ----------
        cursor: clang.Cursor
            The AST node currently being visited.
        filename: str
            Path of the file being checked.

        Returns
        -------
        list[Diagnostic]
            A single diagnostic if the cursor is a disallowed using-statement,
            otherwise an empty list.

        """
        if cursor.kind not in _USING_KINDS:
            return []

        parent = cursor.semantic_parent
        if parent is None or parent.kind not in _GLOBAL_PARENT_KINDS:
            return []

        loc = cursor.location

        if cursor.kind == clang.CursorKind.USING_DIRECTIVE:
            # cursor.spelling is always empty for USING_DIRECTIVE; the namespace
            # name lives in the first NAMESPACE_REF child instead.
            ns_ref = next(
                (
                    c
                    for c in cursor.get_children()
                    if c.kind == clang.CursorKind.NAMESPACE_REF
                ),
                None,
            )
            name = ns_ref.spelling if ns_ref is not None else "<unknown>"
            msg = (
                f"do not use 'using namespace {name}' at namespace/global scope"
                " — confine it to a function body"
            )
        else:
            # USING_DECLARATION: cursor.spelling gives the declared name.
            name = cursor.spelling
            msg = (
                f"do not use 'using {name}' declaration at namespace/global scope"
                " — confine it to a function body"
            )

        return [
            Diagnostic(
                file=filename,
                line=loc.line,
                column=loc.column,
                message=msg,
                check_id=self.id,
                severity="style",
            )
        ]
