"""Flag banned macro invocations and suggest their replacement.

Any macro invocation whose name matches a configured key in
``macro_to_replacement`` is reported, naming the replacement macro that
should be used instead. Built for cases like disallowing gtest's
``EXPECT_THROW``/``ASSERT_THROW`` in favor of custom
``EXPECT_THROW_MSG``/``ASSERT_THROW_MSG`` macros that also require a
failure message, but works for any macro pair.

Detection is based on libclang's ``MACRO_INSTANTIATION`` cursor (available
because the AST engine always parses with
``PARSE_DETAILED_PROCESSING_RECORD``), so it works regardless of whether the
macro is defined in the same file or an included header, and it matches the
macro name exactly — ``EXPECT_THROW`` never accidentally matches
``EXPECT_THROW_MSG``.

Ships with a built-in default mapping and requires no configuration to use::

    EXPECT_THROW -> EXPECT_THROW_MSG
    ASSERT_THROW -> ASSERT_THROW_MSG

Replace or extend it via::

    [cpp.ast_check_config.macroReplacement]
    macro_to_replacement = { EXPECT_THROW = "EXPECT_THROW_MSG",
                             ASSERT_THROW = "ASSERT_THROW_MSG" }

To disable this check for a project set::

    [cpp]
    ast_check_disabled_ids = ["macroReplacement"]
"""

from __future__ import annotations

import clang.cindex as clang

from devops.config.base import ConfigError
from devops.cpp.ast.base import Check, Diagnostic

_DEFAULT_MACRO_TO_REPLACEMENT = {
    "EXPECT_THROW": "EXPECT_THROW_MSG",
    "ASSERT_THROW": "ASSERT_THROW_MSG",
}


class MacroReplacement(Check):
    """Flag invocations of a banned macro and suggest its replacement."""

    id = "macroReplacement"

    def __init__(self) -> None:
        """Initialize with the built-in default macro-to-replacement mapping."""
        self.macro_to_replacement: dict[str, str] = dict(_DEFAULT_MACRO_TO_REPLACEMENT)

    def configure(self, config: dict) -> None:
        """Replace the default macro-to-replacement mapping from the TOML config.

        Parameters
        ----------
        config: dict
            Expected shape:
            ``{"macro_to_replacement": {"OLD_MACRO": "NEW_MACRO", ...}}``.
            When ``macro_to_replacement`` is absent, the built-in default
            mapping is kept unchanged.

        Raises
        ------
        ConfigError
            If ``macro_to_replacement`` is present but has an invalid shape.

        """
        if "macro_to_replacement" not in config:
            return
        raw = config["macro_to_replacement"]
        if not isinstance(raw, dict) or not all(
            isinstance(k, str) and isinstance(v, str) for k, v in raw.items()
        ):
            msg = (
                "macroReplacement: 'macro_to_replacement' must be a table of "
                "string -> string mappings"
            )
            raise ConfigError(msg)
        self.macro_to_replacement = dict(raw)

    def visit(self, cursor: clang.Cursor, filename: str) -> list[Diagnostic]:
        """Flag the cursor if it is an invocation of a banned macro.

        Parameters
        ----------
        cursor: clang.Cursor
            The AST node currently being visited.
        filename: str
            Path of the file being checked.

        Returns
        -------
        list[Diagnostic]
            A single diagnostic if `cursor` is a banned macro invocation,
            otherwise an empty list.

        """
        if cursor.kind != clang.CursorKind.MACRO_INSTANTIATION:
            return []

        name = cursor.spelling
        replacement = self.macro_to_replacement.get(name)
        if replacement is None:
            return []

        loc = cursor.location
        return [
            Diagnostic(
                file=filename,
                line=loc.line,
                column=loc.column,
                message=f"do not use '{name}' — use '{replacement}' instead",
                check_id=self.id,
                severity="style",
            )
        ]
