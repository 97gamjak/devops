"""Flag member functions whose body is written inside the class definition.

Member functions are declared in the class and defined outside of it
(``void Foo::bar() { ... }``), also for classes that live only in a ``.cpp``
file. This keeps class definitions short and readable as an interface.

Flagged are in-class bodies of ordinary, static, operator and conversion
member functions, constructors, destructors and member function templates,
in classes, structs and unions, nested classes and class templates.
Templates are flagged too: their members can still be defined after the
class in the same header (or an included ``.tpp`` file).

Never flagged:

- declarations without a body, pure virtual (``= 0``), ``= default`` and
  ``= delete`` members;
- member functions synthesized by a macro (e.g. ``MSTD_ENUM`` or GTest's
  ``TEST``/``TEST_F``), detected via the macro instantiation that covers the
  member's location;
- members of local classes (declared inside a function body) and of unnamed
  classes, since C++ offers no way to define those outside the class;
- in-class ``friend`` function definitions (hidden friends), which are not
  member functions;
- lambdas, which are expressions rather than member functions.

To disable this check for a project set::

    [cpp]
    ast_check_disabled_ids = ["noInClassMemberDefinition"]
"""

from __future__ import annotations

import typing

import clang.cindex as clang

from devops.cpp.ast.base import Check, Diagnostic

_RECORD_KINDS = frozenset(
    (
        clang.CursorKind.CLASS_DECL,
        clang.CursorKind.STRUCT_DECL,
        clang.CursorKind.UNION_DECL,
        clang.CursorKind.CLASS_TEMPLATE,
        clang.CursorKind.CLASS_TEMPLATE_PARTIAL_SPECIALIZATION,
    )
)

_MEMBER_FUNCTION_KINDS = frozenset(
    (
        clang.CursorKind.CXX_METHOD,
        clang.CursorKind.CONSTRUCTOR,
        clang.CursorKind.DESTRUCTOR,
        clang.CursorKind.CONVERSION_FUNCTION,
        clang.CursorKind.FUNCTION_TEMPLATE,
    )
)

_FUNCTION_SCOPE_KINDS = frozenset(
    (
        *_MEMBER_FUNCTION_KINDS,
        clang.CursorKind.FUNCTION_DECL,
        clang.CursorKind.LAMBDA_EXPR,
    )
)

_SUBJECTS = {
    clang.CursorKind.CONSTRUCTOR: "constructor",
    clang.CursorKind.DESTRUCTOR: "destructor",
    clang.CursorKind.CONVERSION_FUNCTION: "conversion function",
}


class _Span(typing.NamedTuple):
    """Source range of one macro instantiation, as (line, column) pairs."""

    start: tuple[int, int]
    end: tuple[int, int]


class _PendingMember(typing.NamedTuple):
    """A candidate diagnostic buffered until all macro spans are known."""

    subject: str
    record: str
    line: int
    column: int


def _is_out_of_reach(record: clang.Cursor) -> bool:
    """Return whether members of `record` cannot be defined outside it.

    Parameters
    ----------
    record: clang.Cursor
        The class/struct/union the member is lexically declared in.

    Returns
    -------
    bool
        True if `record` or an enclosing record is unnamed, or if `record`
        is a local class (declared inside a function or lambda body).

    """
    scope = record
    while scope is not None and scope.kind != clang.CursorKind.TRANSLATION_UNIT:
        if scope.kind in _FUNCTION_SCOPE_KINDS:
            return True
        if scope.kind in _RECORD_KINDS and scope.is_anonymous():
            return True
        scope = scope.semantic_parent
    return False


def _in_class_record(cursor: clang.Cursor) -> clang.Cursor | None:
    """Return the enclosing record if `cursor` is a member defined in-class.

    Parameters
    ----------
    cursor: clang.Cursor
        Any AST node.

    Returns
    -------
    clang.Cursor | None
        The class/struct/union `cursor` is defined in, or None if `cursor`
        is not a member function with a user-written body inside its class.

    """
    if cursor.kind not in _MEMBER_FUNCTION_KINDS or not cursor.is_definition():
        return None
    record = cursor.lexical_parent
    if record is None or record.kind not in _RECORD_KINDS:
        return None
    # Hidden friends are lexically in the class but belong to the namespace.
    if cursor.semantic_parent != record:
        return None
    if cursor.is_default_method() or cursor.is_deleted_method():
        return None
    if _is_out_of_reach(record):
        return None
    return record


class NoInClassMemberDefinition(Check):
    """Flag member functions defined inside their class body.

    Reporting is deferred to `finalize()`: whether a member was synthesized
    by a macro is only known once every ``MACRO_INSTANTIATION`` cursor in
    the file has been seen.
    """

    id = "noInClassMemberDefinition"

    def __init__(self) -> None:
        """Initialise with empty per-file buffers."""
        self._macro_spans: dict[str, list[_Span]] = {}
        self._pending: dict[str, list[_PendingMember]] = {}

    def visit(self, cursor: clang.Cursor, filename: str) -> list[Diagnostic]:
        """Record macro instantiations and in-class member definitions.

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
            extent = cursor.extent
            self._macro_spans.setdefault(filename, []).append(
                _Span(
                    (extent.start.line, extent.start.column),
                    (extent.end.line, extent.end.column),
                )
            )
            return []

        record = _in_class_record(cursor)
        if record is None:
            return []

        subject = _SUBJECTS.get(cursor.kind, "member function")
        loc = cursor.location
        self._pending.setdefault(filename, []).append(
            _PendingMember(
                f"{subject} '{cursor.spelling}'",
                record.spelling,
                loc.line,
                loc.column,
            )
        )
        return []

    def finalize(self, filename: str) -> list[Diagnostic]:
        """Emit diagnostics for buffered members not produced by a macro.

        Parameters
        ----------
        filename: str
            Path of the file being checked.

        Returns
        -------
        list[Diagnostic]
            One diagnostic per member function defined inside its class.

        """
        spans = self._macro_spans.pop(filename, [])
        pending = self._pending.pop(filename, [])
        return [
            Diagnostic(
                file=filename,
                line=member.line,
                column=member.column,
                message=(
                    f"{member.subject} is defined inside class "
                    f"'{member.record}' — declare it in the class and define "
                    "it outside"
                ),
                check_id=self.id,
                severity="style",
            )
            for member in pending
            if not any(
                span.start <= (member.line, member.column) <= span.end for span in spans
            )
        ]
