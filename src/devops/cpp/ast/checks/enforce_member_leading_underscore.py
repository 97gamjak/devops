"""Enforce a leading underscore on private and protected member variables.

Any non-static or static data member declared under a ``private:`` or
``protected:`` access specifier must have a name starting with ``_``
(e.g. ``_count``, ``_isValid``). Public members are never flagged, since
they are part of the class's external interface and not the concern of
this check.

Member variables synthesized by a macro invoked on the same source line
(e.g. gtest's ``TEST_F(...)`` expanding to a fixture class with its own
private ``test_info_`` member, declared entirely inside gtest's macro body)
are not flagged: the name was never actually typed by the user, so there is
nothing for them to rename.

To disable this check for a project set::

    [cpp]
    ast_check_disabled_ids = ["memberLeadingUnderscore"]
"""

from __future__ import annotations

import typing

import clang.cindex as clang

from devops.cpp.ast.base import Check, Diagnostic

# Cursor kinds of a record whose direct data members this check inspects.
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

_RESTRICTED_ACCESS = frozenset(
    (clang.AccessSpecifier.PRIVATE, clang.AccessSpecifier.PROTECTED)
)


class _PendingMember(typing.NamedTuple):
    """A candidate diagnostic buffered until end-of-file macro info is known."""

    name: str
    access: str
    line: int
    column: int


class EnforceMemberLeadingUnderscore(Check):
    """Flag private/protected member variables without a leading underscore.

    Reporting is deferred to `finalize()` because whether a candidate member
    was synthesized by a macro (and should be skipped) can only be known
    once every ``MACRO_INSTANTIATION`` cursor in the file has been seen —
    which, in a single preorder walk, may happen before or after the member
    itself is visited.
    """

    id = "memberLeadingUnderscore"

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

        if cursor.kind not in _MEMBER_KINDS:
            return []

        if cursor.access_specifier not in _RESTRICTED_ACCESS:
            return []

        parent = cursor.semantic_parent
        if parent is None or parent.kind not in _RECORD_KINDS:
            return []

        name = cursor.spelling
        if not name or name.startswith("_"):
            return []

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
        """Emit diagnostics for buffered members not on a macro-instantiation line.

        Parameters
        ----------
        filename: str
            Path of the file being checked.

        Returns
        -------
        list[Diagnostic]
            One diagnostic per offending member variable whose line isn't
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
                    f"{member.access} member variable '{member.name}' should "
                    f"start with a leading underscore ('_{member.name}')"
                ),
                check_id=self.id,
                severity="style",
            )
            for member in pending
            if member.line not in macro_lines
        ]
