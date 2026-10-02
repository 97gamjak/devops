"""Flag a #include line followed by a comment that isn't an allowed IWYU pragma.

A trailing comment on a ``#include`` line (same line, after the directive)
is only accepted when it is an
`include-what-you-use <https://github.com/include-what-you-use/include-what-you-use>`_
pragma, i.e. matches ``// IWYU pragma: <keyword> ...`` (or the ``/* ... */``
form). Any other trailing comment — a plain note, a disabled-linter comment,
etc. — is reported. An ``#include`` with no trailing comment at all is
always allowed.

To disable this check for a project set::

    [cpp]
    ast_check_disabled_ids = ["includeIwyuPragmaOnly"]

By default every IWYU pragma keyword (``export``, ``keep``, ``no_include``,
``private``, ``associated``, ``friend``, ...) is accepted. Restrict which
keywords are allowed via the per-check table; an empty/unset list keeps the
default of allowing all of them::

    [cpp.ast_check_config.includeIwyuPragmaOnly]
    allowed_pragmas = ["export", "keep"]
"""

from __future__ import annotations

import re

import clang.cindex as clang

from devops.config.base import ConfigError
from devops.cpp.ast.base import Check, Diagnostic

_IWYU_PRAGMA_RE = re.compile(r"^/[/*]\s*IWYU pragma:\s*(\S+)")


class IncludeIwyuPragmaOnly(Check):
    """Flag non-IWYU-pragma trailing comments on #include directives."""

    id = "includeIwyuPragmaOnly"

    def __init__(self) -> None:
        """Initialize with no pragma restriction (every IWYU pragma is allowed)."""
        self.allowed_pragmas: frozenset[str] = frozenset()

    def configure(self, config: dict) -> None:
        """Load the allowed IWYU pragma keywords from the check's TOML config block.

        Parameters
        ----------
        config: dict
            Expected shape: ``{"allowed_pragmas": ["export", "keep"]}``. When
            absent or empty, every IWYU pragma keyword is allowed.

        Raises
        ------
        ConfigError
            If ``allowed_pragmas`` is present but is not a list of strings.

        """
        raw = config.get("allowed_pragmas", [])
        if not isinstance(raw, list) or not all(isinstance(p, str) for p in raw):
            msg = (
                f"{self.id}: 'allowed_pragmas' in "
                f"[cpp.ast_check_config.{self.id}] must be a list of strings"
            )
            raise ConfigError(msg)
        self.allowed_pragmas = frozenset(raw)

    def visit(self, cursor: clang.Cursor, filename: str) -> list[Diagnostic]:
        """Flag the cursor's trailing comment if it is a disallowed one.

        Parameters
        ----------
        cursor: clang.Cursor
            The AST node currently being visited.
        filename: str
            Path of the file being checked.

        Returns
        -------
        list[Diagnostic]
            A single diagnostic if `cursor` is a ``#include`` directive
            followed by a disallowed trailing comment, otherwise an empty
            list.

        """
        if cursor.kind != clang.CursorKind.INCLUSION_DIRECTIVE:
            return []

        comment = self._trailing_comment(cursor)
        if comment is None:
            return []

        loc = cursor.location
        match = _IWYU_PRAGMA_RE.match(comment)
        if match is None:
            return [
                Diagnostic(
                    file=filename,
                    line=loc.line,
                    column=loc.column,
                    message=(
                        f"#include '{cursor.spelling}' is followed by a comment "
                        f"that is not an IWYU pragma ('{comment}') — remove it "
                        "or use a '// IWYU pragma: ...' comment"
                    ),
                    check_id=self.id,
                    severity="style",
                )
            ]

        pragma = match.group(1)
        if self.allowed_pragmas and pragma not in self.allowed_pragmas:
            return [
                Diagnostic(
                    file=filename,
                    line=loc.line,
                    column=loc.column,
                    message=(
                        f"#include '{cursor.spelling}' uses IWYU pragma "
                        f"'{pragma}', which is not in the allowed list "
                        f"{sorted(self.allowed_pragmas)}"
                    ),
                    check_id=self.id,
                    severity="style",
                )
            ]

        return []

    @staticmethod
    def _trailing_comment(cursor: clang.Cursor) -> str | None:
        """Return the comment token right after `cursor`'s #include, if any.

        Parameters
        ----------
        cursor: clang.Cursor
            An ``INCLUSION_DIRECTIVE`` cursor.

        Returns
        -------
        str | None
            The spelling of the first comment token on the same line right
            after the ``#include`` directive, or None if there isn't one.

        """
        end = cursor.extent.end
        file = end.file
        if file is None:
            return None
        translation_unit = cursor.translation_unit
        next_line_start = clang.SourceLocation.from_position(
            translation_unit, file, end.line + 1, 1
        )
        token_range = clang.SourceRange.from_locations(end, next_line_start)
        for token in translation_unit.get_tokens(extent=token_range):
            if token.extent.start.line != end.line:
                break
            if token.kind == clang.TokenKind.COMMENT:
                return token.spelling
        return None
