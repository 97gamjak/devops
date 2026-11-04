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

Patterns are matched with `fnmatch` rules (``*`` matches within a path
component) against the ``#include`` path exactly as written in the source
and against its basename, so both a full relative path and a bare filename
pattern work.
"""

from __future__ import annotations

import clang.cindex as clang

from devops.config.base import ConfigError
from devops.cpp.ast.base import Check, Diagnostic
from devops.cpp.cpp_only_include_scan import matches_cpp_only_header
from devops.files.files import FileType, determine_file_type


class EnforceCppOnlyInclude(Check):
    """Flag #includes of configured cpp-only headers from inside other headers."""

    id = "enforceCppOnlyInclude"

    def __init__(self) -> None:
        """Initialize with no headers configured (check is a no-op)."""
        self.headers: tuple[str, ...] = ()

    def configure(self, config: dict) -> None:
        """Load the patterns identifying headers that are cpp-only.

        Parameters
        ----------
        config: dict
            Expected shape: ``{"libs": ["detail/foo_impl.hpp"]}``. When
            absent or empty, this check never flags anything.

        Raises
        ------
        ConfigError
            If ``libs`` is present but is not a list of strings.

        """
        raw = config.get("libs", [])
        if not isinstance(raw, list) or not all(isinstance(h, str) for h in raw):
            msg = (
                f"{self.id}: 'libs' in [cpp.ast_check_config.{self.id}] must be "
                "a list of strings"
            )
            raise ConfigError(msg)
        self.headers = tuple(raw)

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

        if determine_file_type(filename) != FileType.CPPHeader:
            return []

        include_path = cursor.spelling
        if not matches_cpp_only_header(include_path, self.headers):
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
