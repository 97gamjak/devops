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

To disable this check for a project set::

    [cpp]
    ast_check_disabled_ids = ["classMemberOrder"]
"""

from __future__ import annotations

import clang.cindex as clang

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


class EnforceClassMemberOrder(Check):
    """Flag member variables/functions declared out of the required section order."""

    id = "classMemberOrder"

    def visit(self, cursor: clang.Cursor, filename: str) -> list[Diagnostic]:
        """Check one record's direct children for out-of-order sections.

        Parameters
        ----------
        cursor: clang.Cursor
            The AST node currently being visited.
        filename: str
            Path of the file being checked.

        Returns
        -------
        list[Diagnostic]
            One diagnostic per member declared before a section that must
            precede it (e.g. a member function found before a still-pending
            private member variable section).

        """
        if cursor.kind not in _RECORD_KINDS:
            return []

        diagnostics: list[Diagnostic] = []
        highest_phase_seen = -1
        highest_label = ""

        for child in cursor.get_children():
            category_rank = _category_rank(child.kind)
            if category_rank is None:
                continue
            access_rank = _ACCESS_RANK.get(child.access_specifier)
            if access_rank is None:
                continue

            phase = category_rank * 3 + access_rank
            if phase < highest_phase_seen:
                name = child.spelling or "<unnamed>"
                loc = child.location
                diagnostics.append(
                    Diagnostic(
                        file=filename,
                        line=loc.line,
                        column=loc.column,
                        message=(
                            f"{_PHASE_LABELS[phase]} '{name}' is declared "
                            f"after {highest_label} — a class must declare "
                            "public, protected, then private member "
                            "variables, followed by public, protected, then "
                            "private member functions, in that order"
                        ),
                        check_id=self.id,
                        severity="style",
                    )
                )
                continue

            highest_phase_seen = phase
            highest_label = _PHASE_LABELS[phase]

        return diagnostics
