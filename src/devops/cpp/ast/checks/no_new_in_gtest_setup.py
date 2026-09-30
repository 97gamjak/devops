"""Flag `new` expressions inside a GTest setup function.

A member function named ``SetUp``, ``SetUpTestSuite``, or ``SetUpTestCase``
— the fixture-setup hooks GTest calls by name (``SetUp()`` before every
test, the other two once per test suite) — is reported for any ``new``
expression appearing anywhere in its body. A raw pointer allocated there
needs a matching manual release, and whether that release actually runs
depends on a separate teardown hook firing later (see also
:doc:`noDeleteInGtestTeardown </sections/ast_checks/no_delete_in_gtest_teardown>`)
— if `SetUp()` itself throws partway through, or a later `SetUp()` call in
the same fixture leaks the previous allocation, the memory is never freed.
Prefer ``std::unique_ptr``/``std::shared_ptr`` (or another RAII owner) so
the allocation's lifetime is tied to the fixture object itself rather than
to a hook running at the right time.

Only a literal ``new`` expression lexically inside the setup function's own
body is flagged — a call to some other function that itself allocates is
not traced into.

To disable this check for a project set::

    [cpp]
    ast_check_disabled_ids = ["noNewInGtestSetup"]
"""

from __future__ import annotations

import clang.cindex as clang

from devops.cpp.ast.base import Check, Diagnostic

# GTest calls these fixture methods by name; no base-class relationship is
# required by the framework itself, so none is checked here either.
_SETUP_NAMES = frozenset(
    (
        "SetUp",
        "SetUpTestSuite",
        "SetUpTestCase",
    )
)


class NoNewInGtestSetup(Check):
    """Flag `new` expressions inside a GTest setup function."""

    id = "noNewInGtestSetup"

    def visit(self, cursor: clang.Cursor, filename: str) -> list[Diagnostic]:
        """Flag any new-expression inside a GTest setup function body.

        Parameters
        ----------
        cursor: clang.Cursor
            The AST node currently being visited.
        filename: str
            Path of the file being checked.

        Returns
        -------
        list[Diagnostic]
            One diagnostic per `new` expression found inside `cursor`'s
            body, if `cursor` is a GTest setup function; otherwise an empty
            list.

        """
        if cursor.kind != clang.CursorKind.CXX_METHOD:
            return []
        if cursor.spelling not in _SETUP_NAMES:
            return []
        if not cursor.is_definition():
            return []

        return [
            self._make_diagnostic(new_expr, cursor.spelling, filename)
            for new_expr in cursor.walk_preorder()
            if new_expr.kind == clang.CursorKind.CXX_NEW_EXPR
        ]

    def _make_diagnostic(
        self, new_expr: clang.Cursor, function_name: str, filename: str
    ) -> Diagnostic:
        """Build the diagnostic for one flagged new-expression.

        Parameters
        ----------
        new_expr: clang.Cursor
            The `CXX_NEW_EXPR` cursor to report.
        function_name: str
            Name of the enclosing setup function, for the message.
        filename: str
            Path of the file being checked.

        Returns
        -------
        Diagnostic
            The diagnostic for `new_expr`.

        """
        loc = new_expr.location
        return Diagnostic(
            file=filename,
            line=loc.line,
            column=loc.column,
            message=(
                f"do not use 'new' inside GTest setup function "
                f"'{function_name}()' — prefer an RAII/smart-pointer owner "
                "whose lifetime doesn't depend on a later teardown hook"
            ),
            check_id=self.id,
            severity="style",
        )
