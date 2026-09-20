"""Base interface for libclang AST-based C++ checks.

Every check is a small class implementing `Check`. A single shared AST
walk (see `devops.cpp.ast.engine.run_ast_checks`) dispatches each cursor
to every registered check's `visit()`, so adding a new check never costs
another parse/walk pass over the file.
"""

from __future__ import annotations

import typing
from dataclasses import dataclass

if typing.TYPE_CHECKING:
    import clang.cindex as clang


@dataclass(frozen=True)
class Diagnostic:
    """A single issue found by an AST check at a specific source location."""

    file: str
    line: int
    column: int
    message: str
    check_id: str
    severity: str = "style"

    def format(self) -> str:
        """Format the diagnostic in a cppcheck-style single line.

        Returns
        -------
        str
            The formatted diagnostic, e.g.
            ``foo.cpp:12:5: style: <message> [<check_id>]``.

        """
        return (
            f"{self.file}:{self.line}:{self.column}: {self.severity}: "
            f"{self.message} [{self.check_id}]"
        )


class Check:
    """Base class every custom AST check must subclass.

    Not an ABC: both `visit` and `finalize` have usable no-op defaults, so
    a check only needs to override whichever one it actually uses.
    """

    #: unique id, used as the cppcheck-style [id] suffix
    id: str = "unnamed-check"

    def visit(self, cursor: clang.Cursor, filename: str) -> list[Diagnostic]:
        """Inspect a single AST node during the shared preorder walk.

        Called once per AST node in `filename`. Override to inspect
        `cursor` and return zero or more Diagnostics. The default
        implementation does nothing, which is useful for checks that only
        need `finalize`.

        Parameters
        ----------
        cursor: clang.Cursor
            The AST node currently being visited.
        filename: str
            Path of the file being checked.

        Returns
        -------
        list[Diagnostic]
            Diagnostics raised by this node, if any.

        """
        del cursor, filename
        return []

    def global_finalize(self) -> bool:
        """Call after ALL files have been checked.

        Override for post-run validation, such as warning about configured
        type names that were never encountered in any file's AST. The default
        implementation does nothing and returns True (no errors).

        Returns
        -------
        bool
            True if no errors were found, False if the check should be
            considered failed (e.g. a configured type was never seen and
            ``unseen_type_is_error`` is enabled).

        """
        return True

    def configure(self, config: dict) -> None:
        """Apply check-specific configuration from the user's TOML block.

        Called once during setup with the sub-table keyed by this check's
        `.id` in ``cpp.ast_check_config``. Override to read your check's
        own settings. The default implementation ignores all config.

        Parameters
        ----------
        config: dict
            The raw configuration dict for this check, e.g.
            ``{"type_to_name": {"SimulationBox": "simulationBox"}}``.

        """
        del config

    def finalize(self, filename: str) -> list[Diagnostic]:
        """Run once after the whole file's AST has been walked.

        Override for checks needing whole-translation-unit state (counts,
        cross-references) rather than a single-node check.

        Parameters
        ----------
        filename: str
            Path of the file being checked.

        Returns
        -------
        list[Diagnostic]
            Diagnostics raised at end-of-file, if any.

        """
        del filename
        return []
