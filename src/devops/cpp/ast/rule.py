"""Rule adapter exposing the AST-check engine through devops's Rule interface."""

from __future__ import annotations

import typing

import clang.cindex as clang

from devops.cpp.ast.engine import run_ast_checks
from devops.cpp.ast.registry import ALL_CHECKS, configure_checks, select_checks
from devops.logger import cpp_check_logger
from devops.rules import ResultType, ResultTypeEnum, Rule, RuleInputType, RuleType

if typing.TYPE_CHECKING:
    from pathlib import Path

    from devops.rules import FileRuleInput

DEFAULT_COMPILE_ARGS = ["-std=c++23"]

# Flags that are not useful to libclang and whose following argument (if any)
# should also be dropped.
_SKIP_WITH_ARG = frozenset(("-o", "-MF", "-MT", "-MQ"))
# Flags that are not useful but take no following argument.
_SKIP_ALONE = frozenset((
    "-c",
    # Turn-error-into-error flags: too strict for static analysis where we
    # only care about AST structure, not compilation correctness.
    "-Werror",
    "-pedantic-errors",
))
# Source / header file extensions to skip when they appear as positional args.
_SOURCE_EXTENSIONS = (".cpp", ".cxx", ".cc", ".c", ".hpp", ".hxx", ".hh", ".h")


def _args_from_compile_commands(
    db: clang.CompilationDatabase, path: Path
) -> list[str] | None:
    """Return filtered compile args for *path* from *db*, or None if not found."""
    cmds = db.getCompileCommands(str(path.resolve()))
    if not cmds:
        return None

    raw = list(cmds[0].arguments)  # first element is the compiler executable
    result: list[str] = []
    it = iter(raw[1:])  # skip compiler executable
    for arg in it:
        # '--' marks the end of flags; everything after is an input file path.
        if arg == "--":
            break
        if arg in _SKIP_WITH_ARG:
            next(it, None)  # drop the following argument too
            continue
        if arg in _SKIP_ALONE:
            continue
        # Skip source / header files passed as positional arguments.
        if not arg.startswith("-") and arg.endswith(_SOURCE_EXTENSIONS):
            continue
        # Handle -Xclang <frontend-arg> pairs.  Drop -include-pch entirely
        # (the .gch file may not exist for every cmake target and causes a
        # hard parse failure).  All other -Xclang pairs are kept as-is.
        if arg == "-Xclang":
            xclang_arg = next(it, None)
            if xclang_arg == "-include-pch":
                next(it, None)  # skip following -Xclang
                next(it, None)  # skip the .gch file path
                continue
            if xclang_arg is not None:
                result.append(arg)
                result.append(xclang_arg)
            continue
        result.append(arg)
    # Clang/libclang compatibility: silently ignore GCC-only flags that
    # would otherwise cause libclang to reject the translation unit.
    result += ["-Wno-unknown-warning-option", "-Wno-unused-command-line-argument"]
    return result


class ASTChecksRule(Rule):
    """Run every enabled libclang AST-based check in a single pass.

    Slots into `build_cpp_rules` as one ordinary FILE rule: each file is
    parsed once by libclang, and every enabled check in
    `devops.cpp.ast.registry.ALL_CHECKS` is dispatched against that single
    AST walk. All diagnostics found are combined into one ResultType.
    """

    def __init__(
        self,
        compile_args: list[str] | None = None,
        compile_commands_db: str | None = None,
        enabled_check_ids: list[str] | None = None,
        disabled_check_ids: list[str] | None = None,
        check_config: dict[str, dict] | None = None,
    ) -> None:
        """Initialize ASTChecksRule.

        Parameters
        ----------
        compile_args: list[str] | None
            Fallback compiler flags passed to libclang when parsing each file.
            Used when ``compile_commands_db`` is not set or the file is not
            found in the database. Defaults to `DEFAULT_COMPILE_ARGS`.
        compile_commands_db: str | None
            Path to the directory containing ``compile_commands.json``
            (e.g. ``"build"``).  When set, per-file compile flags are looked
            up from the database, falling back to ``compile_args`` if the
            file is not listed.
        enabled_check_ids: list[str] | None
            If non-empty, only checks whose `.id` is in this list run
            (see `devops.cpp.ast.registry.select_checks`).
        disabled_check_ids: list[str] | None
            Checks whose `.id` is in this list never run.
        check_config: dict[str, dict] | None
            Per-check configuration keyed by check id (from
            ``cpp.ast_check_config`` in the project TOML). Passed to
            each check's ``configure()`` method.

        """
        self.compile_args = compile_args or DEFAULT_COMPILE_ARGS
        self._compile_db: clang.CompilationDatabase | None = None
        if compile_commands_db is not None:
            try:
                self._compile_db = clang.CompilationDatabase.fromDirectory(
                    compile_commands_db
                )
            except clang.CompilationDatabaseError:
                cpp_check_logger.warning(
                    f"AST checks: could not load compile_commands.json from "
                    f"'{compile_commands_db}' — falling back to compile_args."
                )

        self.checks = configure_checks(
            select_checks(
                ALL_CHECKS,
                enabled_ids=enabled_check_ids,
                disabled_ids=disabled_check_ids,
            ),
            check_config,
        )

        super().__init__(
            name="ASTChecks",
            description="Run all enabled libclang AST-based C++ checks.",
            rule_type=RuleType.CPP_STYLE,
            rule_input_type=RuleInputType.FILE,
            func=self._run,
        )

    def _run(self, file_rule_input: FileRuleInput) -> ResultType:
        """Run all enabled AST checks against a single file.

        Parameters
        ----------
        file_rule_input: FileRuleInput
            The file content and path to check.

        Returns
        -------
        ResultType
            Ok if no check reported anything; otherwise an Error whose
            description lists every diagnostic found, one per line.

        """
        if file_rule_input.path is None:
            return ResultType(ResultTypeEnum.Ok)

        compile_args = self.compile_args
        if self._compile_db is not None:
            per_file = _args_from_compile_commands(
                self._compile_db, file_rule_input.path
            )
            if per_file is not None:
                compile_args = per_file
            else:
                cpp_check_logger.debug(
                    f"AST checks: '{file_rule_input.path}' not in compile_commands.json"
                    " — using fallback compile_args."
                )

        diagnostics = run_ast_checks(
            file_rule_input.path,
            file_rule_input.file_content,
            compile_args,
            checks=self.checks,
        )

        if not diagnostics:
            return ResultType(ResultTypeEnum.Ok)

        description = "\n" + "\n".join(d.format() for d in diagnostics)
        return ResultType(ResultTypeEnum.Error, description)

    def finalize_run(self) -> bool:
        """Call global_finalize() on every active check after all files are done.

        Returns
        -------
        bool
            True if all checks passed, False if any check reported an error.

        """
        return all(check.global_finalize() for check in self.checks)
