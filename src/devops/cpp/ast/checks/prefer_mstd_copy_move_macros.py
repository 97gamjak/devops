"""Flag hand-written deleted copy/move members that a macro should replace.

Code bases using mstd delete copy and move operations with
``MSTD_NO_COPY(X)`` and ``MSTD_NO_MOVE(X)`` instead of spelling out::

    X(const X &) = delete;
    X &operator=(const X &) = delete;
    X(X &&) = delete;
    X &operator=(X &&) = delete;

Members produced by a macro expansion (``MSTD_NO_COPY``, ``MSTD_NO_MOVE``,
``MSTD_RAII_NO_MOVE``, ...) are not flagged: only a ``= delete`` written in
the checked file's own tokens is.

The suggested macro names are configurable:

    [cpp.ast_check_config.preferMstdCopyMoveMacros]
    copy_macro = "MSTD_NO_COPY"
    move_macro = "MSTD_NO_MOVE"

To disable this check for a project set::

    [cpp]
    ast_check_disabled_ids = ["preferMstdCopyMoveMacros"]
"""

from __future__ import annotations

import itertools
import re

import clang.cindex as clang

from devops.config.base import ConfigError
from devops.cpp.ast.base import Check, Diagnostic

_MEMBER_KINDS = (clang.CursorKind.CONSTRUCTOR, clang.CursorKind.CXX_METHOD)
_IDENTIFIER = re.compile(r"[A-Za-z_]\w*")


def _special_member(cursor: clang.Cursor) -> tuple[str, bool] | None:
    """Classify `cursor` as a copy/move special member.

    Parameters
    ----------
    cursor: clang.Cursor
        A ``CONSTRUCTOR`` or ``CXX_METHOD`` cursor.

    Returns
    -------
    tuple[str, bool] | None
        A human-readable member name and whether it is a copy (``True``) or
        move (``False``) member, or None for any other function.

    """
    if cursor.kind == clang.CursorKind.CONSTRUCTOR:
        if cursor.is_copy_constructor():
            return "copy constructor", True
        if cursor.is_move_constructor():
            return "move constructor", False
        return None
    if cursor.is_copy_assignment_operator_method():
        return "copy assignment operator", True
    if cursor.is_move_assignment_operator_method():
        return "move assignment operator", False
    return None


def _has_written_delete(cursor: clang.Cursor) -> bool:
    """Check whether ``= delete`` is spelled in `cursor`'s own tokens.

    A member produced by a macro expansion has the macro invocation as its
    extent, so its tokens never contain ``= delete``.

    Parameters
    ----------
    cursor: clang.Cursor
        The member declaration.

    Returns
    -------
    bool
        True if the tokens contain ``=`` directly followed by ``delete``.

    """
    spellings = [t.spelling for t in cursor.get_tokens()]
    return any(
        first == "=" and second == "delete"
        for first, second in itertools.pairwise(spellings)
    )


class PreferMstdCopyMoveMacros(Check):
    """Flag hand-written ``= delete`` copy/move constructors and assignments."""

    id = "preferMstdCopyMoveMacros"

    def __init__(self) -> None:
        """Initialise with the mstd macro names."""
        self.copy_macro = "MSTD_NO_COPY"
        self.move_macro = "MSTD_NO_MOVE"

    def configure(self, config: dict) -> None:
        """Load the suggested macro names from the check's TOML config block.

        Parameters
        ----------
        config: dict
            Optional keys ``copy_macro`` and ``move_macro``, each a macro
            name (C identifier).

        Raises
        ------
        ConfigError
            If a configured macro name is not a valid identifier string.

        """
        for key in ("copy_macro", "move_macro"):
            if key not in config:
                continue
            value = config[key]
            if not isinstance(value, str) or not _IDENTIFIER.fullmatch(value):
                msg = (
                    f"preferMstdCopyMoveMacros: '{key}' must be a macro name "
                    f"(identifier), got {value!r}"
                )
                raise ConfigError(msg)
            setattr(self, key, value)

    def visit(self, cursor: clang.Cursor, filename: str) -> list[Diagnostic]:
        """Flag a hand-written deleted copy/move constructor or assignment.

        Parameters
        ----------
        cursor: clang.Cursor
            The AST node currently being visited.
        filename: str
            Path of the file being checked.

        Returns
        -------
        list[Diagnostic]
            A single diagnostic if `cursor` is a hand-written deleted
            copy/move member, otherwise an empty list.

        """
        if cursor.kind not in _MEMBER_KINDS:
            return []
        member = _special_member(cursor)
        if member is None or not _has_written_delete(cursor):
            return []

        name, is_copy = member
        macro = self.copy_macro if is_copy else self.move_macro
        class_name = cursor.semantic_parent.spelling.split("<", 1)[0]
        loc = cursor.location
        return [
            Diagnostic(
                file=filename,
                line=loc.line,
                column=loc.column,
                message=(
                    f"deleted {name} of '{class_name}' is written by hand "
                    f"— use {macro}({class_name}) instead"
                ),
                check_id=self.id,
            )
        ]
