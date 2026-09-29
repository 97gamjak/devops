"""Enforce a fixed section order for member variables and member functions.

Within a single class/struct/union body (including templates), the direct
members must appear grouped, in exactly this order:

1. public member variables
2. protected member variables
3. private member variables
4. public member functions
5. protected member functions
6. private member functions

Anything not covered by that list — nested types, ``using`` declarations,
enums, friend declarations, ``static_assert``, the access specifiers
themselves — is ignored for ordering purposes: it neither has to fit
anywhere in particular nor resets the sequence.

Only declarations that lexically appear inside the class body are
considered, so an out-of-line member-function definition
(``void C::f() { ... }``) never affects its class's ordering — only the
in-class declaration does.

Declarations synthesized by a configured macro (matched by the macro's own
name, at its invocation line) are excluded entirely from ordering: they are
neither flagged themselves nor counted when checking what came before or
after them — exactly like the nested-type/using-declaration exclusions
above. This is for macros such as Qt's ``Q_OBJECT`` that expand to
boilerplate members (and possibly their own access-specifier changes) whose
position isn't the author's choice::

    [cpp.ast_check_config.classMemberOrder]
    excluded_macros = ["Q_OBJECT", "MY_DECLARE_PROPERTY"]

To disable this check entirely for a project set::

    [cpp]
    ast_check_disabled_ids = ["classMemberOrder"]
"""

from __future__ import annotations

import typing

import clang.cindex as clang

from devops.config.base import ConfigError
from devops.cpp.ast.base import Check, Diagnostic

# Record kinds whose direct children this check inspects.
_RECORD_KINDS = frozenset(
    (
        clang.CursorKind.CLASS_DECL,
        clang.CursorKind.STRUCT_DECL,
        clang.CursorKind.UNION_DECL,
        clang.CursorKind.CLASS_TEMPLATE,
        clang.CursorKind.CLASS_TEMPLATE_PARTIAL_SPECIALIZATION,
    )
)

# FIELD_DECL covers non-static data members; a direct VAR_DECL child of a
# record is a static data member (ordinary VAR_DECLs elsewhere aren't
# children of a record cursor at all, so no extra filtering is needed here).
_MEMBER_VARIABLE_KINDS = frozenset(
    (clang.CursorKind.FIELD_DECL, clang.CursorKind.VAR_DECL)
)

# CXX_METHOD covers ordinary (including static and operator) methods,
# CONSTRUCTOR/DESTRUCTOR cover special member functions, CONVERSION_FUNCTION
# covers `operator T() const`-style conversions, and FUNCTION_TEMPLATE covers
# member function templates.
_MEMBER_FUNCTION_KINDS = frozenset(
    (
        clang.CursorKind.CXX_METHOD,
        clang.CursorKind.CONSTRUCTOR,
        clang.CursorKind.DESTRUCTOR,
        clang.CursorKind.CONVERSION_FUNCTION,
        clang.CursorKind.FUNCTION_TEMPLATE,
    )
)

_ACCESS_RANK = {
    clang.AccessSpecifier.PUBLIC: 0,
    clang.AccessSpecifier.PROTECTED: 1,
    clang.AccessSpecifier.PRIVATE: 2,
}

# Indexed by phase (category-rank * 3 + access-rank): the required order is
# public/protected/private member variables, then public/protected/private
# member functions.
_PHASE_LABELS = (
    "a public member variable",
    "a protected member variable",
    "a private member variable",
    "a public member function",
    "a protected member function",
    "a private member function",
)


def _category_rank(kind: clang.CursorKind) -> int | None:
    """Classify a direct record-member cursor kind for ordering purposes.

    Parameters
    ----------
    kind: clang.CursorKind
        The cursor kind of a direct child of a class/struct/union.

    Returns
    -------
    int | None
        0 for a member variable, 1 for a member function, or None if `kind`
        isn't relevant to this check's ordering (nested types, using
        declarations, access specifiers, ...).

    """
    if kind in _MEMBER_VARIABLE_KINDS:
        return 0
    if kind in _MEMBER_FUNCTION_KINDS:
        return 1
    return None


class _PendingMember(typing.NamedTuple):
    """A classified record member, buffered until end-of-file macro info is known."""

    phase: int
    name: str
    line: int
    column: int


class EnforceClassMemberOrder(Check):
    """Flag member variables/functions declared out of the required section order.

    Reporting is deferred to `finalize()`: a macro invoked inside a class
    body (e.g. ``Q_OBJECT``) shows up in libclang's preprocessing record as
    a cursor local to the translation unit rather than as a lexical child of
    the class, and may be visited before or after the class itself in a
    single preorder walk. Whether a given member's line is covered by an
    *excluded* macro invocation can therefore only be known once the whole
    file has been walked.
    """

    id = "classMemberOrder"

    def __init__(self) -> None:
        """Initialise with no macros excluded and empty per-file buffers."""
        self._excluded_macros: frozenset[str] = frozenset()
        self._macro_lines: dict[str, set[int]] = {}
        self._pending_records: dict[str, list[list[_PendingMember]]] = {}

    def configure(self, config: dict) -> None:
        """Load the ``excluded_macros`` list from the check's TOML config block.

        Parameters
        ----------
        config: dict
            Expected shape: ``{"excluded_macros": ["Q_OBJECT"]}``.

        Raises
        ------
        ConfigError
            If ``excluded_macros`` is present but is not a list of strings.

        """
        raw = config.get("excluded_macros", [])
        if not isinstance(raw, list) or not all(isinstance(n, str) for n in raw):
            msg = (
                f"{self.id}: 'excluded_macros' in "
                f"[cpp.ast_check_config.{self.id}] must be a list of strings"
            )
            raise ConfigError(msg)
        self._excluded_macros = frozenset(raw)

    def visit(self, cursor: clang.Cursor, filename: str) -> list[Diagnostic]:
        """Record excluded-macro lines and classify one record's direct children.

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
            if cursor.spelling in self._excluded_macros:
                lines = self._macro_lines.setdefault(filename, set())
                lines.update(
                    range(cursor.extent.start.line, cursor.extent.end.line + 1)
                )
            return []

        if cursor.kind not in _RECORD_KINDS:
            return []

        members: list[_PendingMember] = []
        for child in cursor.get_children():
            category_rank = _category_rank(child.kind)
            if category_rank is None:
                continue
            access_rank = _ACCESS_RANK.get(child.access_specifier)
            if access_rank is None:
                continue

            loc = child.location
            members.append(
                _PendingMember(
                    phase=category_rank * 3 + access_rank,
                    name=child.spelling or "<unnamed>",
                    line=loc.line,
                    column=loc.column,
                )
            )

        self._pending_records.setdefault(filename, []).append(members)
        return []

    def finalize(self, filename: str) -> list[Diagnostic]:
        """Evaluate ordering for every record buffered for `filename`.

        Parameters
        ----------
        filename: str
            Path of the file being checked.

        Returns
        -------
        list[Diagnostic]
            One diagnostic per member declared before a section that must
            precede it, skipping members whose line is covered by an
            excluded macro invocation.

        """
        macro_lines = self._macro_lines.pop(filename, set())
        records = self._pending_records.pop(filename, [])

        diagnostics: list[Diagnostic] = []
        for members in records:
            highest_phase_seen = -1
            highest_label = ""
            for member in members:
                if member.line in macro_lines:
                    continue

                if member.phase < highest_phase_seen:
                    diagnostics.append(
                        Diagnostic(
                            file=filename,
                            line=member.line,
                            column=member.column,
                            message=(
                                f"{_PHASE_LABELS[member.phase]} '{member.name}' "
                                f"is declared after {highest_label} — a class "
                                "must declare public, protected, then private "
                                "member variables, followed by public, "
                                "protected, then private member functions, in "
                                "that order"
                            ),
                            check_id=self.id,
                            severity="style",
                        )
                    )
                    continue

                highest_phase_seen = member.phase
                highest_label = _PHASE_LABELS[member.phase]

        return diagnostics
