"""Flag top-level ``const`` on parameters passed by value.

A by-value parameter is a local copy, so marking it ``const`` adds nothing to
the function's interface and only adds noise: ``void f(const int x)`` should
be ``void f(int x)``. The same holds for a ``const`` pointer itself
(``int *const p``). Pointers to const (``const int *p``) and references
(``const T &``, ``T &&``) are not affected.

clang-tidy's ``readability-avoid-const-params-in-decls`` only covers
declarations; this check also covers definitions and lambdas. Only a ``const``
written in the parameter itself is flagged: ``const`` coming from a type alias
or a macro, unnamed parameters, parameters of deleted or defaulted functions
and parameters inside function types (e.g. function pointers) are ignored.

To disable this check for a project set::

    [cpp]
    ast_check_disabled_ids = ["noConstValueParam"]
"""

from __future__ import annotations

import clang.cindex as clang

from devops.cpp.ast.base import Check, Diagnostic

_FUNCTION_KINDS = (
    clang.CursorKind.FUNCTION_DECL,
    clang.CursorKind.FUNCTION_TEMPLATE,
    clang.CursorKind.CXX_METHOD,
    clang.CursorKind.CONSTRUCTOR,
    clang.CursorKind.CONVERSION_FUNCTION,
    clang.CursorKind.LAMBDA_EXPR,
)

_METHOD_KINDS = (clang.CursorKind.CXX_METHOD, clang.CursorKind.CONSTRUCTOR)

_REFERENCE_KINDS = (
    clang.TypeKind.LVALUEREFERENCE,
    clang.TypeKind.RVALUEREFERENCE,
)


def _written_const(cursor: clang.Cursor) -> bool:
    """Check whether ``const`` is spelled before the parameter's name.

    Parameters
    ----------
    cursor: clang.Cursor
        A named `PARM_DECL` cursor.

    Returns
    -------
    bool
        True if a ``const`` token precedes the name token. False if there is
        none or the name is not found at the cursor's location (e.g. the
        parameter comes from a macro expansion).

    """
    start_offset = cursor.extent.start.offset
    name_offset = cursor.location.offset
    seen_const = False
    for token in cursor.get_tokens():
        # libclang also yields macro-definition tokens before the extent.
        if token.location.offset < start_offset:
            continue
        if token.spelling == cursor.spelling and token.location.offset == name_offset:
            return seen_const
        if token.spelling == "const":
            seen_const = True
    return False


def _is_deleted_or_defaulted(function: clang.Cursor) -> bool:
    """Check whether `function` is declared ``= delete`` or ``= default``.

    Parameters
    ----------
    function: clang.Cursor
        The function-like cursor owning the parameter.

    Returns
    -------
    bool
        True if `function` is deleted (reported as unavailable) or a
        defaulted method.

    """
    if function.kind == clang.CursorKind.LAMBDA_EXPR:
        return False
    if function.availability == clang.AvailabilityKind.NOT_AVAILABLE:
        return True
    return function.kind in _METHOD_KINDS and function.is_default_method()


class NoConstValueParam(Check):
    """Flag a by-value parameter declared with top-level ``const``."""

    id = "noConstValueParam"

    def visit(self, cursor: clang.Cursor, filename: str) -> list[Diagnostic]:
        """Flag the cursor if it is a ``const`` by-value parameter.

        Parameters
        ----------
        cursor: clang.Cursor
            The AST node currently being visited.
        filename: str
            Path of the file being checked.

        Returns
        -------
        list[Diagnostic]
            A single diagnostic if `cursor` is a named function, method or
            lambda parameter whose own type is ``const`` and not a
            reference, otherwise an empty list.

        """
        if cursor.kind != clang.CursorKind.PARM_DECL or not cursor.spelling:
            return []
        param_type = cursor.type
        if param_type.kind in _REFERENCE_KINDS or not param_type.is_const_qualified():
            return []
        function = cursor.semantic_parent
        if function is None or function.kind not in _FUNCTION_KINDS:
            return []
        if not _written_const(cursor) or _is_deleted_or_defaulted(function):
            return []

        loc = cursor.location
        return [
            Diagnostic(
                file=filename,
                line=loc.line,
                column=loc.column,
                message=(
                    f"parameter '{cursor.spelling}' is passed by value as "
                    f"'{param_type.spelling}' — drop the top-level 'const'"
                ),
                check_id=self.id,
                severity="style",
            )
        ]
