"""Flag headers that may only be #included from .cpp files.

Some headers are implementation details of a single translation unit (e.g.
a ``*_impl.hpp`` meant to be included at the bottom of exactly one ``.cpp``)
and must never be pulled into another header, which would leak that
translation unit's dependencies into every file that transitively includes
it. This check flags an ``#include`` of a configured header whenever it
appears inside another header; including the same header directly from a
``.cpp`` file is always allowed.

Configure which headers are cpp-only via the per-check table; an
empty/unset list disables the check entirely::

    [cpp.ast_check_config.enforceCppOnlyInclude]
    libs = ["detail/foo_impl.hpp", "*_internal.hpp"]

Patterns are matched with `fnmatch` rules against the ``#include`` path
exactly as written in the source — never against just its basename, so a
pattern of ``"units.hpp"`` matches a bare ``#include "units.hpp"`` but not
``#include <mstd/units.hpp>``, a same-named header from a different
library. `fnmatch`'s ``*`` matches across ``/`` too, so a pattern like
``"*/units.hpp"`` or ``"*_impl.hpp"`` still matches regardless of
directory.

A header that itself wraps or defines a cpp-only header (and must
therefore include it unconditionally) can be exempted via
``exclude_paths``, matched against the *including* file's path using the
same rules as `devops.cpp.ast.checks.name_filtered`'s ``path_exceptions``
(a trailing ``/`` matches a directory prefix; anything else is an
`fnmatch` glob)::

    [cpp.ast_check_config.enforceCppOnlyInclude]
    libs = ["units.hpp"]
    exclude_paths = ["include/config/units.hpp"]

By default every header is checked. Set ``extensions`` to restrict the
check to including files with one of the listed extensions only::

    [cpp.ast_check_config.enforceCppOnlyInclude]
    libs = ["units.hpp"]
    extensions = [".tpp"]
"""

from __future__ import annotations

import clang.cindex as clang

from devops.config.base import ConfigError
from devops.cpp.ast.base import Check, Diagnostic
from devops.cpp.cpp_only_include_scan import is_checked_file, matches_cpp_only_header
from devops.cpp.path_patterns import matches_path


class EnforceCppOnlyInclude(Check):
    """Flag #includes of configured cpp-only headers from inside other headers."""

    id = "enforceCppOnlyInclude"

    def __init__(self) -> None:
        """Initialize with no headers configured (check is a no-op)."""
        self.headers: tuple[str, ...] = ()
        self.exclude_paths: tuple[str, ...] = ()
        self.extensions: tuple[str, ...] = ()

    def configure(self, config: dict) -> None:
        """Load the patterns identifying headers that are cpp-only.

        Parameters
        ----------
        config: dict
            Expected shape: ``{"libs": ["detail/foo_impl.hpp"],
            "exclude_paths": ["include/config/"], "extensions": [".tpp"]}``.
            When ``libs`` is absent or empty, this check never flags anything.

        Raises
        ------
        ConfigError
            If ``libs``, ``exclude_paths`` or ``extensions`` is present but
            is not a list of strings.

        """
        self.headers = tuple(self._parse_str_list(config, "libs"))
        self.exclude_paths = tuple(self._parse_str_list(config, "exclude_paths"))
        self.extensions = tuple(self._parse_str_list(config, "extensions"))

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
        """Flag the cursor if it's an #include of a cpp-only header in a header.

        Parameters
        ----------
        cursor: clang.Cursor
            The AST node currently being visited.
        filename: str
            Path of the file being checked.

        Returns
        -------
        list[Diagnostic]
            A single diagnostic if `cursor` is an ``#include`` directive
            that pulls a configured cpp-only header into another header,
            otherwise an empty list.

        """
        if not self.headers or cursor.kind != clang.CursorKind.INCLUSION_DIRECTIVE:
            return []

        if not is_checked_file(filename, self.extensions):
            return []

        include_path = cursor.spelling
        if not matches_cpp_only_header(include_path, self.headers):
            return []

        if any(matches_path(filename, pattern) for pattern in self.exclude_paths):
            return []

        loc = cursor.location
        return [
            Diagnostic(
                file=filename,
                line=loc.line,
                column=loc.column,
                message=(
                    f'#include "{include_path}" is only allowed from .cpp '
                    "files, not from other header files"
                ),
                check_id=self.id,
                severity="style",
            )
        ]
