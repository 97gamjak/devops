"""Flag 'using namespace' directives and using declarations at namespace/global scope.

Any ``using namespace X;`` or ``using X::Y;`` that appears directly inside a
translation unit or a named/anonymous namespace is reported as an error.
Identical constructs inside a function, lambda, or class body are silently
allowed because their effect is confined to that scope. ``using enum X;`` is
handled by the separate `noGlobalUsingEnum` check.

To disable this check for a project set::

    [cpp]
    ast_check_disabled_ids = ["noGlobalUsing"]

To restrict the check to (or exempt) specific names, use the per-check table.
Names are matched exactly against the qualified name as written in the source
(``std``, ``std::literals``, ``std::string``); a leading ``::`` is ignored::

    [cpp.ast_check_config.noGlobalUsing]
    # Only flag these names (allowlist; empty/unset means "flag everything") ...
    enabled_names = ["std"]
    # ... and never flag these (applied on top of enabled_names).
    disabled_names = ["std::literals", "std::chrono_literals"]
"""

from __future__ import annotations

import clang.cindex as clang

from devops.cpp.ast.base import Diagnostic
from devops.cpp.ast.checks.name_filtered import NameFilteredCheck

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


class NoGlobalUsing(NameFilteredCheck):
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

        # The qualified name as written is the concatenation of the child
        # references: NAMESPACE_REFs for each qualifier, plus (for a using
        # declaration) a final ref for the declared entity. cursor.spelling
        # is empty for USING_DIRECTIVE, so it cannot be used there.
        name = (
            "::".join(c.spelling for c in cursor.get_children() if c.spelling)
            or cursor.spelling
        )

        if not self._is_selected(name):
            return []

        if cursor.kind == clang.CursorKind.USING_DIRECTIVE:
            name = name or "<unknown>"
            msg = (
                f"do not use 'using namespace {name}' at namespace/global scope"
                " — confine it to a function body"
            )
        else:
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
