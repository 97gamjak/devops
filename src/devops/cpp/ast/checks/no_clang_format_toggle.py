"""Flag ``// clang-format off`` / ``// clang-format on`` comments in code.

These comments disable clang-format's formatting for the region they
bracket (or the rest of the file, if unbalanced), letting hand-formatted
code drift silently out of sync with the project's style over time. Both
the line-comment (``// clang-format off``) and block-comment
(``/* clang-format off */``) spellings are flagged, for both ``off`` and
``on``.

To disable this check for a project set::

    [cpp]
    ast_check_disabled_ids = ["noClangFormatToggle"]
"""

from __future__ import annotations

import re

import clang.cindex as clang

from devops.cpp.ast.base import Check, Diagnostic

_CLANG_FORMAT_TOGGLE_RE = re.compile(
    r"^/[/*]\s*clang-format\s+(off|on)\s*\*?/?$"
)


class NoClangFormatToggle(Check):
    """Flag ``// clang-format off``/``on`` comments anywhere in the file."""

    id = "noClangFormatToggle"

    def __init__(self) -> None:
        """Initialize with no translation units captured yet."""
        self._translation_units: dict[str, tuple[clang.TranslationUnit, str]] = {}

    def visit(self, cursor: clang.Cursor, filename: str) -> list[Diagnostic]:
        """Capture the file's translation unit for `finalize`'s token scan.

        Comments aren't exposed as AST cursors, so this check can't flag
        anything from a single cursor. Instead it piggybacks on the shared
        walk just to remember `cursor`'s translation unit (and the resolved
        file name libclang matched it under), then does the real work once
        in `finalize`.

        Parameters
        ----------
        cursor: clang.Cursor
            The AST node currently being visited.
        filename: str
            Path of the file being checked.

        Returns
        -------
        list[Diagnostic]
            Always empty — diagnostics are emitted from `finalize`.

        """
        if filename not in self._translation_units:
            self._translation_units[filename] = (
                cursor.translation_unit,
                cursor.location.file.name,
            )
        return []

    def finalize(self, filename: str) -> list[Diagnostic]:
        """Scan the file's comment tokens for clang-format toggle comments.

        Parameters
        ----------
        filename: str
            Path of the file being checked.

        Returns
        -------
        list[Diagnostic]
            One diagnostic per ``// clang-format off``/``on`` comment found
            in `filename` itself (comments pulled in from other headers via
            the AST are ignored).

        """
        entry = self._translation_units.pop(filename, None)
        if entry is None:
            return []
        translation_unit, resolved_name = entry

        # `translation_unit.cursor.extent` only spans the *parsed* file — for
        # a header checked via the engine's `#include`-wrapper trick (see
        # `run_ast_checks`), that's the synthetic wrapper, not the header
        # itself, so tokens physically located in the header are outside it
        # and would silently be skipped. Build the extent directly from the
        # header/file's own `File` object instead, covering it end-to-end
        # regardless of which file libclang actually parsed. An
        # out-of-bounds end position is clamped by libclang to the file's
        # last valid location rather than raising.
        file = clang.File.from_name(translation_unit, resolved_name)
        start_loc = clang.SourceLocation.from_position(translation_unit, file, 1, 1)
        end_loc = clang.SourceLocation.from_position(
            translation_unit, file, 2**31 - 1, 1
        )
        extent = clang.SourceRange.from_locations(start_loc, end_loc)

        diagnostics = []
        for token in translation_unit.get_tokens(extent=extent):
            if token.kind != clang.TokenKind.COMMENT:
                continue
            start = token.extent.start
            if start.file is None or start.file.name != resolved_name:
                continue
            match = _CLANG_FORMAT_TOGGLE_RE.match(token.spelling.strip())
            if match is None:
                continue
            diagnostics.append(
                Diagnostic(
                    file=filename,
                    line=start.line,
                    column=start.column,
                    message=(
                        f"do not use '{token.spelling.strip()}' to toggle "
                        "clang-format — keep the code consistently formatted "
                        "instead"
                    ),
                    check_id=self.id,
                    severity="style",
                )
            )
        return diagnostics
