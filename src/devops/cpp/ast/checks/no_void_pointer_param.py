"""Forbid ``void *`` parameters in public and protected functions.

A function that is reachable from other translation units or other classes
should offer a typed API: a ``void *`` (or ``const void *``, ``void **``,
...) parameter erases the type and moves every mistake from compile time to
run time. Any parameter whose type is a pointer to ``void`` at any pointer
level (after resolving typedefs and aliases, and also through a reference
such as ``void *&``) is flagged on

- free functions and function templates with external linkage,
- public and protected member functions, member function templates and
  constructors.

Not flagged, because they are not part of a public API or their signature
is fixed elsewhere:

- private member functions, ``static`` free functions and anything in an
  anonymous namespace or a local class (these may wrap C APIs),
- ``extern "C"`` declarations,
- deleted functions (``= delete``, commonly used to reject conversions),
- methods overriding a base-class virtual method,
- function pointer parameters (e.g. ``void (*cb)(void *)``) and parameters
  of a dependent template type,
- functions and parameters whose name comes from a macro expansion (e.g.
  generated test bodies).

Out-of-line definitions are only reported at their first declaration, so a
method declared in a header and defined in a ``.cpp`` file is reported once.

To disable this check for a project set::

    [cpp]
    ast_check_disabled_ids = ["noVoidPointerParam"]
"""

from __future__ import annotations

import typing

import clang.cindex as clang

from devops.cpp.ast.base import Check, Diagnostic
from devops.cpp.ast.checks.enforce_no_public_leading_underscore import (
    _overrides_base_method,
)

_FUNCTION_KINDS = frozenset(
    (
        clang.CursorKind.FUNCTION_DECL,
        clang.CursorKind.CXX_METHOD,
        clang.CursorKind.CONSTRUCTOR,
        clang.CursorKind.FUNCTION_TEMPLATE,
    )
)

_INTERNAL_LINKAGES = frozenset(
    (
        clang.LinkageKind.NO_LINKAGE,
        clang.LinkageKind.INTERNAL,
        clang.LinkageKind.UNIQUE_EXTERNAL,
    )
)


def _is_void_pointer(ty: clang.Type) -> bool:
    """Return whether `ty` is a pointer to ``void`` at any pointer level.

    Parameters
    ----------
    ty: clang.Type
        The parameter's type.

    Returns
    -------
    bool
        True for ``void *``, ``const void *``, ``void **``, ``void *&`` and
        aliases of those; False for everything else, including function
        pointers.

    """
    ty = ty.get_canonical()
    if ty.kind in (clang.TypeKind.LVALUEREFERENCE, clang.TypeKind.RVALUEREFERENCE):
        ty = ty.get_pointee().get_canonical()
    if ty.kind != clang.TypeKind.POINTER:
        return False
    while ty.kind == clang.TypeKind.POINTER:
        ty = ty.get_pointee().get_canonical()
    return ty.kind == clang.TypeKind.VOID


def _is_deleted(cursor: clang.Cursor) -> bool:
    """Return whether the function at `cursor` is deleted (``= delete``)."""
    return cursor.availability == clang.AvailabilityKind.NOT_AVAILABLE


def _is_extern_c(cursor: clang.Cursor) -> bool:
    """Return whether `cursor` is declared inside an ``extern "C"`` block."""
    parent = cursor.lexical_parent
    while parent is not None and parent.kind != clang.CursorKind.TRANSLATION_UNIT:
        if parent.kind == clang.CursorKind.LINKAGE_SPEC:
            return True
        parent = parent.lexical_parent
    return False


def _is_exempt(cursor: clang.Cursor) -> bool:
    """Return whether the function at `cursor` may take ``void *`` parameters.

    Parameters
    ----------
    cursor: clang.Cursor
        A function, method, constructor or function template cursor.

    Returns
    -------
    bool
        True if the function is private, has internal or no linkage, is
        ``extern "C"``, deleted, an override, or not its first declaration.

    """
    if cursor.canonical != cursor:
        return True
    if cursor.access_specifier == clang.AccessSpecifier.PRIVATE:
        return True
    if cursor.linkage in _INTERNAL_LINKAGES:
        return True
    if _is_extern_c(cursor) or _is_deleted(cursor):
        return True
    return cursor.kind == clang.CursorKind.CXX_METHOD and _overrides_base_method(cursor)


def _parameters(cursor: clang.Cursor) -> list[clang.Cursor]:
    """Return the direct parameters of a function or function template."""
    if cursor.kind == clang.CursorKind.FUNCTION_TEMPLATE:
        return [
            c for c in cursor.get_children() if c.kind == clang.CursorKind.PARM_DECL
        ]
    return list(cursor.get_arguments())


class _Pending(typing.NamedTuple):
    """A candidate diagnostic buffered until all macro expansions are known."""

    function: str
    param: str
    type_name: str
    line: int
    column: int
    function_line: int
    function_column: int


def _in_ranges(line: int, column: int, ranges: list[tuple[int, int, int, int]]) -> bool:
    """Return whether ``line:column`` lies inside one of `ranges`."""
    return any(
        (start_line, start_col) <= (line, column) <= (end_line, end_col)
        for start_line, start_col, end_line, end_col in ranges
    )


class NoVoidPointerParam(Check):
    """Flag ``void *`` parameters of public and protected functions.

    Reporting is deferred to `finalize()` so that functions and parameters
    whose name comes from a macro expansion can be skipped once every
    ``MACRO_INSTANTIATION`` of the file is known.
    """

    id = "noVoidPointerParam"

    def __init__(self) -> None:
        """Initialise with empty per-file buffers."""
        self._macro_ranges: dict[str, list[tuple[int, int, int, int]]] = {}
        self._pending: dict[str, list[_Pending]] = {}

    def visit(self, cursor: clang.Cursor, filename: str) -> list[Diagnostic]:
        """Record macro expansions and ``void *`` parameters of `cursor`.

        Parameters
        ----------
        cursor: clang.Cursor
            The AST node currently being visited.
        filename: str
            Path of the file being checked.

        Returns
        -------
        list[Diagnostic]
            Always empty; diagnostics are emitted from `finalize()`.

        """
        if cursor.kind == clang.CursorKind.MACRO_INSTANTIATION:
            start, end = cursor.extent.start, cursor.extent.end
            self._macro_ranges.setdefault(filename, []).append(
                (start.line, start.column, end.line, end.column)
            )
            return []
        if cursor.kind not in _FUNCTION_KINDS:
            return []
        params = [p for p in _parameters(cursor) if _is_void_pointer(p.type)]
        if not params or _is_exempt(cursor):
            return []

        pending = self._pending.setdefault(filename, [])
        for param in params:
            pending.append(
                _Pending(
                    cursor.spelling,
                    param.spelling,
                    param.type.spelling,
                    param.location.line,
                    param.location.column,
                    cursor.location.line,
                    cursor.location.column,
                )
            )
        return []

    def finalize(self, filename: str) -> list[Diagnostic]:
        """Emit diagnostics for buffered parameters not named by a macro.

        Parameters
        ----------
        filename: str
            Path of the file being checked.

        Returns
        -------
        list[Diagnostic]
            One diagnostic per offending parameter.

        """
        ranges = self._macro_ranges.pop(filename, [])
        diagnostics = []
        for item in self._pending.pop(filename, []):
            if _in_ranges(item.line, item.column, ranges) or _in_ranges(
                item.function_line, item.function_column, ranges
            ):
                continue
            name = f"'{item.param}'" if item.param else "(unnamed)"
            diagnostics.append(
                Diagnostic(
                    file=filename,
                    line=item.line,
                    column=item.column,
                    message=(
                        f"parameter {name} of '{item.function}' has type "
                        f"'{item.type_name}'; public and protected functions "
                        "need a typed parameter instead of void *"
                    ),
                    check_id=self.id,
                )
            )
        return diagnostics
