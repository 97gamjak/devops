"""Enforce a leading underscore on private and protected member functions.

Any ordinary member function (including static and template member
functions) declared under a ``private:`` or ``protected:`` access specifier
must have a name starting with ``_`` (e.g. ``_compute``, ``_isReady``).
Public member functions are never flagged, since they are part of the
class's external interface and not the concern of this check.

A handful of member-function kinds are never flagged, because their name is
fixed by the language or by a base class and renaming them isn't something
the author can freely do:

- Constructors and destructors — their name is always the class's own name
  (or ``~ClassName``).
- Operator overloads and conversion functions (``operator==``,
  ``operator[]``, ``operator int() const``, ...) — the operator's spelling
  is fixed by the language grammar.
- Methods that override a base class's virtual method — the override must
  keep the base method's exact name to bind at all.

As with `memberLeadingUnderscore`, a member function synthesized by a macro
invoked on the same source line is not flagged either.

To disable this check for a project set::

    [cpp]
    ast_check_disabled_ids = ["memberFunctionLeadingUnderscore"]
"""

from __future__ import annotations

import ctypes
import typing

import clang.cindex as clang
from clang.cindex import conf

from devops.cpp.ast.base import Check, Diagnostic

# Cursor kinds of a record whose direct member functions this check inspects.
_RECORD_KINDS = frozenset(
    (
        clang.CursorKind.CLASS_DECL,
        clang.CursorKind.STRUCT_DECL,
        clang.CursorKind.UNION_DECL,
        clang.CursorKind.CLASS_TEMPLATE,
        clang.CursorKind.CLASS_TEMPLATE_PARTIAL_SPECIALIZATION,
    )
)

# CXX_METHOD covers ordinary (including static and operator) methods,
# CONVERSION_FUNCTION covers `operator T() const`-style conversions, and
# FUNCTION_TEMPLATE covers member function templates. Constructors and
# destructors are deliberately excluded — see the module docstring.
_MEMBER_FUNCTION_KINDS = frozenset(
    (
        clang.CursorKind.CXX_METHOD,
        clang.CursorKind.CONVERSION_FUNCTION,
        clang.CursorKind.FUNCTION_TEMPLATE,
    )
)

_RESTRICTED_ACCESS = frozenset(
    (clang.AccessSpecifier.PRIVATE, clang.AccessSpecifier.PROTECTED)
)

_overridden_cursors_bound = False


def _bind_overridden_cursors_ctypes() -> None:
    """Bind the ctypes signatures for the two libclang functions used below.

    ``clang_getOverriddenCursors()``/``clang_disposeOverriddenCursors()``
    have no high-level wrapper in this libclang Python binding, so they're
    bound here directly via ctypes (a stable part of the public libclang C
    API since LLVM 3.x). Deferred to first use — rather than run at import
    time — so that importing this module (e.g. when Sphinx documents it with
    ``clang`` mocked out because libclang isn't installed) doesn't require a
    real ``clang.Cursor`` ctypes type.
    """
    global _overridden_cursors_bound
    if _overridden_cursors_bound:
        return
    conf.lib.clang_getOverriddenCursors.restype = None
    conf.lib.clang_getOverriddenCursors.argtypes = [
        clang.Cursor,
        ctypes.POINTER(ctypes.POINTER(clang.Cursor)),
        ctypes.POINTER(ctypes.c_uint),
    ]
    conf.lib.clang_disposeOverriddenCursors.restype = None
    conf.lib.clang_disposeOverriddenCursors.argtypes = [ctypes.POINTER(clang.Cursor)]
    _overridden_cursors_bound = True


def _is_restricted_member_function(cursor: clang.Cursor) -> bool:
    """Return whether `cursor` is a private/protected member function candidate.

    Parameters
    ----------
    cursor: clang.Cursor
        The AST node to check.

    Returns
    -------
    bool
        True if `cursor` is a member function this check should inspect for
        a leading underscore.

    """
    if cursor.kind not in _MEMBER_FUNCTION_KINDS:
        return False
    if cursor.access_specifier not in _RESTRICTED_ACCESS:
        return False
    parent = cursor.semantic_parent
    if parent is None or parent.kind not in _RECORD_KINDS:
        return False
    name = cursor.spelling
    if not name or name.startswith(("_", "operator")):
        return False
    return not _overrides_base_method(cursor)


def _overrides_base_method(cursor: clang.Cursor) -> bool:
    """Return whether `cursor` overrides at least one base-class method.

    Parameters
    ----------
    cursor: clang.Cursor
        A ``CXX_METHOD`` (or similar) cursor to check.

    Returns
    -------
    bool
        True if `cursor` overrides one or more base-class virtual methods.

    """
    _bind_overridden_cursors_ctypes()
    overridden = ctypes.POINTER(clang.Cursor)()
    count = ctypes.c_uint()
    conf.lib.clang_getOverriddenCursors(
        cursor, ctypes.byref(overridden), ctypes.byref(count)
    )
    has_override = count.value > 0
    if has_override:
        conf.lib.clang_disposeOverriddenCursors(overridden)
    return has_override


class _PendingMember(typing.NamedTuple):
    """A candidate diagnostic buffered until end-of-file macro info is known."""

    name: str
    access: str
    line: int
    column: int


class EnforceMemberFunctionLeadingUnderscore(Check):
    """Flag private/protected member functions without a leading underscore.

    Reporting is deferred to `finalize()` for the same reason as in
    `EnforceMemberLeadingUnderscore`: whether a candidate was synthesized by
    a macro can only be known once every ``MACRO_INSTANTIATION`` cursor in
    the file has been seen.
    """

    id = "memberFunctionLeadingUnderscore"

    def __init__(self) -> None:
        """Initialise with empty per-file buffers."""
        self._macro_lines: dict[str, set[int]] = {}
        self._pending: dict[str, list[_PendingMember]] = {}

    def visit(self, cursor: clang.Cursor, filename: str) -> list[Diagnostic]:
        """Record macro-instantiation lines and candidate methods for `filename`.

        Parameters
        ----------
        cursor: clang.Cursor
            The AST node currently being visited.
        filename: str
            Path of the file being checked.

        Returns
        -------
        list[Diagnostic]
            Always empty — diagnostics are emitted from `finalize()` once
            the whole file (including its macro instantiations) is known.

        """
        if cursor.kind == clang.CursorKind.MACRO_INSTANTIATION:
            lines = self._macro_lines.setdefault(filename, set())
            lines.update(range(cursor.extent.start.line, cursor.extent.end.line + 1))
            return []

        if not _is_restricted_member_function(cursor):
            return []

        name = cursor.spelling
        access = (
            "private"
            if cursor.access_specifier == clang.AccessSpecifier.PRIVATE
            else "protected"
        )
        loc = cursor.location
        self._pending.setdefault(filename, []).append(
            _PendingMember(name, access, loc.line, loc.column)
        )
        return []

    def finalize(self, filename: str) -> list[Diagnostic]:
        """Emit diagnostics for buffered methods not on a macro-instantiation line.

        Parameters
        ----------
        filename: str
            Path of the file being checked.

        Returns
        -------
        list[Diagnostic]
            One diagnostic per offending member function whose line isn't
            covered by a macro instantiation.

        """
        macro_lines = self._macro_lines.pop(filename, set())
        pending = self._pending.pop(filename, [])
        return [
            Diagnostic(
                file=filename,
                line=member.line,
                column=member.column,
                message=(
                    f"{member.access} member function '{member.name}' should "
                    f"start with a leading underscore ('_{member.name}')"
                ),
                check_id=self.id,
                severity="style",
            )
            for member in pending
            if member.line not in macro_lines
        ]
