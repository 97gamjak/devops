"""Flag ``#include`` directives of libraries that must never be included.

Some libraries (e.g. ``mp-units``) must not be pulled into a code base at
all. This check flags every ``#include`` whose path matches one of the
configured patterns, whether written with quotes or angle brackets, in any
file.

Patterns are matched against the ``#include`` path exactly as written in the
source. A pattern matches if it equals the path (with `fnmatch` rules, where
``*`` also matches ``/``) or if it names a directory prefix, so a bare
library name excludes the library and all of its subfiles::

    [cpp.ast_check_config.noForbiddenInclude]
    libs = ["mp-units", "boost/hana.hpp", "*_deprecated.hpp"]

``mp-units`` above matches ``<mp-units/systems/si.h>`` as well as
``<mp-units/core.h>``. Files that are allowed to include a forbidden library
anyway can be exempted via ``exclude_paths`` (a trailing ``/`` matches a
directory prefix; anything else is an `fnmatch` glob)::

    [cpp.ast_check_config.noForbiddenInclude]
    libs = ["mp-units"]
    exclude_paths = ["src/units/"]

An empty/unset ``libs`` list disables the check entirely.
"""

from __future__ import annotations

import fnmatch

import clang.cindex as clang

from devops.config.base import ConfigError
from devops.cpp.ast.base import Check, Diagnostic
from devops.cpp.path_patterns import matches_path


def matches_forbidden_include(include_path: str, patterns: tuple[str, ...]) -> bool:
    """Return whether `include_path` matches any forbidden-library pattern.

    Parameters
    ----------
    include_path: str
        The path of the ``#include`` as written in the source.
    patterns: tuple[str, ...]
        Library names, directory prefixes or `fnmatch` globs.

    Returns
    -------
    bool
        True if a pattern equals the path, matches it as a glob, or names a
        directory containing it.

    """
    for pattern in patterns:
        prefix = pattern.rstrip("/")
        if fnmatch.fnmatchcase(include_path, pattern) or fnmatch.fnmatchcase(
            include_path, f"{prefix}/*"
        ):
            return True
    return False


class NoForbiddenInclude(Check):
    """Flag #includes of configured libraries that must never be included."""

    id = "noForbiddenInclude"

    def __init__(self) -> None:
        """Initialize with no libraries configured (check is a no-op)."""
        self.libs: tuple[str, ...] = ()
        self.exclude_paths: tuple[str, ...] = ()

    def configure(self, config: dict) -> None:
        """Load the forbidden library patterns.

        Parameters
        ----------
        config: dict
            Expected shape: ``{"libs": ["mp-units"], "exclude_paths":
            ["src/units/"]}``. When ``libs`` is absent or empty, this check
            never flags anything.

        Raises
        ------
        ConfigError
            If ``libs`` or ``exclude_paths`` is present but is not a list of
            strings, or if the table contains any other (e.g. misspelled) key.

        """
        unknown = sorted(set(config) - {"libs", "exclude_paths"})
        if unknown:
            msg = (
                f"{self.id}: unknown key(s) {unknown} in "
                f"[cpp.ast_check_config.{self.id}]; expected 'libs' and/or "
                "'exclude_paths'"
            )
            raise ConfigError(msg)
        self.libs = tuple(self._parse_str_list(config, "libs"))
        self.exclude_paths = tuple(self._parse_str_list(config, "exclude_paths"))

    def _parse_str_list(self, config: dict, key: str) -> list[str]:
        raw = config.get(key, [])
        if not isinstance(raw, list) or not all(isinstance(h, str) for h in raw):
            msg = (
                f"{self.id}: '{key}' in [cpp.ast_check_config.{self.id}] must be "
                "a list of strings"
            )
            raise ConfigError(msg)
        return raw

    def visit(self, cursor: clang.Cursor, filename: str) -> list[Diagnostic]:
        """Flag the cursor if it's an #include of a forbidden library.

        Parameters
        ----------
        cursor: clang.Cursor
            The AST node currently being visited.
        filename: str
            Path of the file being checked.

        Returns
        -------
        list[Diagnostic]
            A single diagnostic if `cursor` is an ``#include`` directive of a
            forbidden library, otherwise an empty list.

        """
        if not self.libs or cursor.kind != clang.CursorKind.INCLUSION_DIRECTIVE:
            return []

        include_path = cursor.spelling
        if not matches_forbidden_include(include_path, self.libs):
            return []

        if any(matches_path(filename, pattern) for pattern in self.exclude_paths):
            return []

        loc = cursor.location
        return [
            Diagnostic(
                file=filename,
                line=loc.line,
                column=loc.column,
                message=f'#include "{include_path}" is forbidden by the project '
                "configuration",
                check_id=self.id,
                severity="style",
            )
        ]
