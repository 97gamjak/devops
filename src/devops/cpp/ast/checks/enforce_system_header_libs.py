"""Flag `#include "lib/..."` for libraries that must be included as system headers.

Some libraries are always meant to be included with angle brackets (e.g.
``#include <mstd/foo.hpp>``), never with quotes (``#include "mstd/foo.hpp"``).
This check flags any ``#include`` whose path's first directory component
matches one of the configured library names but uses quotes instead of
angle brackets.

To disable this check for a project set::

    [cpp]
    ast_check_disabled_ids = ["enforceSystemHeaderLibs"]

Configure which libraries must be included as system headers via the
per-check table; an empty/unset list disables the check entirely::

    [cpp.ast_check_config.enforceSystemHeaderLibs]
    libs = ["mstd"]
"""

from __future__ import annotations

import clang.cindex as clang

from devops.config.base import ConfigError
from devops.cpp.ast.base import Check, Diagnostic

# Minimum token count for an #include directive: '#', 'include', and the
# path itself (either a single quoted LITERAL or a '<' PUNCTUATION token).
_MIN_INCLUDE_TOKENS = 3


class EnforceSystemHeaderLibs(Check):
    """Flag quoted #includes of configured libraries that must use <...>."""

    id = "enforceSystemHeaderLibs"

    def __init__(self) -> None:
        """Initialize with no libraries configured (check is a no-op)."""
        self.libs: frozenset[str] = frozenset()

    def configure(self, config: dict) -> None:
        """Load the set of library names that must be included as system headers.

        Parameters
        ----------
        config: dict
            Expected shape: ``{"libs": ["mstd"]}``. When absent or empty,
            this check never flags anything.

        Raises
        ------
        ConfigError
            If ``libs`` is present but is not a list of strings.

        """
        raw = config.get("libs", [])
        if not isinstance(raw, list) or not all(isinstance(lib, str) for lib in raw):
            msg = (
                f"{self.id}: 'libs' in [cpp.ast_check_config.{self.id}] must be "
                "a list of strings"
            )
            raise ConfigError(msg)
        self.libs = frozenset(raw)

    def visit(self, cursor: clang.Cursor, filename: str) -> list[Diagnostic]:
        """Flag the cursor if it's a quoted #include of a configured library.

        Parameters
        ----------
        cursor: clang.Cursor
            The AST node currently being visited.
        filename: str
            Path of the file being checked.

        Returns
        -------
        list[Diagnostic]
            A single diagnostic if `cursor` is an ``#include`` directive that
            pulls in a configured library via quotes instead of angle
            brackets, otherwise an empty list.

        """
        if not self.libs or cursor.kind != clang.CursorKind.INCLUSION_DIRECTIVE:
            return []

        include_path = cursor.spelling
        lib = include_path.split("/", 1)[0]
        if lib not in self.libs:
            return []

        if self._is_angle_include(cursor) is not False:
            # True (already angle-bracketed) or None (tokens couldn't be
            # inspected) — nothing to flag either way.
            return []

        loc = cursor.location
        return [
            Diagnostic(
                file=filename,
                line=loc.line,
                column=loc.column,
                message=(
                    f'#include "{include_path}" must use a system header '
                    f"include for library '{lib}': use "
                    f"'#include <{include_path}>' instead"
                ),
                check_id=self.id,
                severity="style",
            )
        ]

    @staticmethod
    def _is_angle_include(cursor: clang.Cursor) -> bool | None:
        """Return whether `cursor`'s #include uses angle brackets.

        Parameters
        ----------
        cursor: clang.Cursor
            An ``INCLUSION_DIRECTIVE`` cursor.

        Returns
        -------
        bool | None
            True for ``#include <...>``, False for ``#include "..."``, or
            None if the directive's tokens couldn't be inspected.

        """
        translation_unit = cursor.translation_unit
        tokens = list(translation_unit.get_tokens(extent=cursor.extent))
        # Tokens are '#', 'include', then either a single '"path"' LITERAL
        # token or a '<' PUNCTUATION token starting the bracketed path.
        if len(tokens) < _MIN_INCLUDE_TOKENS:
            return None
        return tokens[2].spelling.startswith("<")
