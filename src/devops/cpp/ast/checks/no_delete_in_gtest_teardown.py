"""Flag `delete`/`delete[]` expressions inside a GTest teardown function.

A member function named ``TearDown``, ``TearDownTestSuite``, or
``TearDownTestCase`` — the fixture-teardown hooks GTest calls by name
(``TearDown()`` after every test, the other two once per test suite) — is
reported for any ``delete``/``delete[]`` expression appearing anywhere in
its body. Manually deleting a raw pointer there is exactly the kind of
lifetime bookkeeping RAII/smart pointers exist to make unnecessary, and it's
especially fragile in a teardown hook: if ``SetUp()`` throws or returns
early, the matching ``delete`` in ``TearDown()`` never runs, and if a test
body already frees the pointer, the ``TearDown()`` delete double-frees it.
Prefer ``std::unique_ptr``/``std::shared_ptr`` (or another RAII owner) for
anything the fixture needs to release, so its lifetime doesn't depend on a
teardown hook running at all.

Only a literal ``delete``/``delete[]`` lexically inside the teardown
function's own body is flagged — a call to some other function that itself
deletes something is not traced into.

To disable this check for a project set::

    [cpp]
    ast_check_disabled_ids = ["noDeleteInGtestTeardown"]
"""

from __future__ import annotations

import clang.cindex as clang

from devops.cpp.ast.base import Check, Diagnostic

# GTest calls these fixture methods by name; no base-class relationship is
# required by the framework itself, so none is checked here either.
_TEARDOWN_NAMES = frozenset(
    (
        "TearDown",
        "TearDownTestSuite",
        "TearDownTestCase",
    )
)


class NoDeleteInGtestTeardown(Check):
    """Flag `delete`/`delete[]` expressions inside a GTest teardown function."""

    id = "noDeleteInGtestTeardown"

    def visit(self, cursor: clang.Cursor, filename: str) -> list[Diagnostic]:
        """Flag any delete-expression inside a GTest teardown function body.

        Parameters
        ----------
        cursor: clang.Cursor
            The AST node currently being visited.
        filename: str
            Path of the file being checked.

        Returns
        -------
        list[Diagnostic]
            One diagnostic per `delete`/`delete[]` expression found inside
            `cursor`'s body, if `cursor` is a GTest teardown function;
            otherwise an empty list.

        """
        if cursor.kind != clang.CursorKind.CXX_METHOD:
            return []
        if cursor.spelling not in _TEARDOWN_NAMES:
            return []
        if not cursor.is_definition():
            return []

        return [
            self._make_diagnostic(delete_expr, cursor.spelling, filename)
            for delete_expr in cursor.walk_preorder()
            if delete_expr.kind == clang.CursorKind.CXX_DELETE_EXPR
        ]

    def _make_diagnostic(
        self, delete_expr: clang.Cursor, function_name: str, filename: str
    ) -> Diagnostic:
        """Build the diagnostic for one flagged delete-expression.

        Parameters
        ----------
        delete_expr: clang.Cursor
            The `CXX_DELETE_EXPR` cursor to report.
        function_name: str
            Name of the enclosing teardown function, for the message.
        filename: str
            Path of the file being checked.

        Returns
        -------
        Diagnostic
            The diagnostic for `delete_expr`.

        """
        tokens = [t.spelling for t in delete_expr.get_tokens()]
        spelling = "delete[]" if tokens[1:2] == ["["] else "delete"
        loc = delete_expr.location
        return Diagnostic(
            file=filename,
            line=loc.line,
            column=loc.column,
            message=(
                f"do not use '{spelling}' inside GTest teardown function "
                f"'{function_name}()' — prefer an RAII/smart-pointer owner "
                "whose lifetime doesn't depend on teardown running"
            ),
            check_id=self.id,
            severity="style",
        )
