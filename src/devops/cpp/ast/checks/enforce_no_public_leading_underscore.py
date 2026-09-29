"""Forbid a leading underscore on public member variables and functions.

Any data member or member function (including static and template ones)
declared under a ``public:`` access specifier — or under no access
specifier at all in a ``struct``/``union`` — must have a name that does
*not* start with ``_`` (e.g. ``count``, ``compute()``, not ``_count`` /
``_compute()``). A leading underscore is reserved for private/protected
members by :doc:`memberLeadingUnderscore
</sections/ast_checks/enforce_member_leading_underscore>` and
:doc:`memberFunctionLeadingUnderscore
</sections/ast_checks/enforce_member_function_leading_underscore>`, so on a
public member it signals the wrong access level or a stray rename rather
than being the author's real intent. Private/protected members are never
flagged here — that's the concern of the two checks above.

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

A member declared entirely inside a macro invoked on the same source line
(e.g. gtest's ``TEST_F(...)`` expanding to a fixture class with its own
public members) is not flagged either: the name was never actually typed by
the user, so there is nothing for them to rename.

To disable this check for a project set::

    [cpp]
    ast_check_disabled_ids = ["noPublicLeadingUnderscore"]
"""

from __future__ import annotations

import ctypes
import typing

import clang.cindex as clang
from clang.cindex import conf

from devops.cpp.ast.base import Check, Diagnostic

# Cursor kinds of a record whose direct members/methods this check inspects.
_RECORD_KINDS = frozenset(
    (
        clang.CursorKind.CLASS_DECL,
        clang.CursorKind.STRUCT_DECL,
        clang.CursorKind.UNION_DECL,
        clang.CursorKind.CLASS_TEMPLATE,
        clang.CursorKind.CLASS_TEMPLATE_PARTIAL_SPECIALIZATION,
    )
)

# FIELD_DECL covers non-static data members; a static data member is a
# VAR_DECL whose semantic parent is the record itself (filtered via
# _RECORD_KINDS below, since VAR_DECL also covers ordinary local/global
# variables).
_MEMBER_KINDS = frozenset((clang.CursorKind.FIELD_DECL, clang.CursorKind.VAR_DECL))

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


def _bind_overridden_cursors_ctypes() -> None:
    """Bind the ctypes signatures for the two libclang functions used below.

    Deferred to first use — rather than run at import time — so that
    importing this module (e.g. when Sphinx documents it with ``clang``
    mocked out because libclang isn't installed) doesn't require a real
    ``clang.Cursor`` ctypes type. Idempotent: checks whether the signature
    is already bound instead of relying on a mutable module-level flag.
    """
    if conf.lib.clang_getOverriddenCursors.argtypes is not None:
        return
    conf.lib.clang_getOverriddenCursors.restype = None
    conf.lib.clang_getOverriddenCursors.argtypes = [
        clang.Cursor,
        ctypes.POINTER(ctypes.POINTER(clang.Cursor)),
        ctypes.POINTER(ctypes.c_uint),
    ]
    conf.lib.clang_disposeOverriddenCursors.restype = None
    conf.lib.clang_disposeOverriddenCursors.argtypes = [ctypes.POINTER(clang.Cursor)]


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


def _is_public_candidate_member(cursor: clang.Cursor) -> bool:
    """Return whether `cursor` is a public data-member candidate.

    Parameters
    ----------
    cursor: clang.Cursor
        The AST node to check.

    Returns
    -------
    bool
        True if `cursor` is a public member variable this check should
        inspect for a leading underscore.

    """
    if cursor.kind not in _MEMBER_KINDS:
        return False
    if cursor.access_specifier != clang.AccessSpecifier.PUBLIC:
        return False
    parent = cursor.semantic_parent
    if parent is None or parent.kind not in _RECORD_KINDS:
        return False
    return bool(cursor.spelling)


def _is_public_candidate_function(cursor: clang.Cursor) -> bool:
    """Return whether `cursor` is a public member-function candidate.

    Parameters
    ----------
    cursor: clang.Cursor
        The AST node to check.

    Returns
    -------
    bool
        True if `cursor` is a public member function this check should
        inspect for a leading underscore.

    """
    if cursor.kind not in _MEMBER_FUNCTION_KINDS:
        return False
    if cursor.access_specifier != clang.AccessSpecifier.PUBLIC:
        return False
    parent = cursor.semantic_parent
    if parent is None or parent.kind not in _RECORD_KINDS:
        return False
    name = cursor.spelling
    if not name or name.startswith("operator"):
        return False
    return not _overrides_base_method(cursor)


class _PendingMember(typing.NamedTuple):
    """A candidate diagnostic buffered until end-of-file macro info is known."""

    name: str
    kind: str
    line: int
    column: int


class EnforceNoPublicLeadingUnderscore(Check):
    """Flag public member variables/functions whose name starts with `_`.

    Reporting is deferred to `finalize()` because whether a candidate member
    was synthesized by a macro (and should be skipped) can only be known
    once every ``MACRO_INSTANTIATION`` cursor in the file has been seen —
    which, in a single preorder walk, may happen before or after the member
    itself is visited.
    """

    id = "noPublicLeadingUnderscore"

    def __init__(self) -> None:
        """Initialise with empty per-file buffers."""
        self._macro_lines: dict[str, set[int]] = {}
        self._pending: dict[str, list[_PendingMember]] = {}

    def visit(self, cursor: clang.Cursor, filename: str) -> list[Diagnostic]:
        """Record macro-instantiation lines and candidate members for `filename`.

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

        if _is_public_candidate_member(cursor):
            kind = "member variable"
        elif _is_public_candidate_function(cursor):
            kind = "member function"
        else:
            return []

        name = cursor.spelling
        if not name.startswith("_"):
            return []

        loc = cursor.location
        self._pending.setdefault(filename, []).append(
            _PendingMember(name, kind, loc.line, loc.column)
        )
        return []

    def finalize(self, filename: str) -> list[Diagnostic]:
        """Emit diagnostics for buffered members not on a macro-instantiation line.

        Parameters
        ----------
        filename: str
            Path of the file being checked.

        Returns
        -------
        list[Diagnostic]
            One diagnostic per offending public member whose line isn't
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
                    f"public {member.kind} '{member.name}' should not start "
                    f"with a leading underscore ('{member.name.lstrip('_')}')"
                ),
                check_id=self.id,
                severity="style",
            )
            for member in pending
            if member.line not in macro_lines
        ]
