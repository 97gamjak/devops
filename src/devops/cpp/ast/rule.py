"""Rule adapter exposing the AST-check engine through devops's Rule interface."""

from __future__ import annotations

import typing
from dataclasses import dataclass
from pathlib import Path

import clang.cindex as clang

from devops.cpp.ast.engine import _with_auto_resource_dir, run_ast_checks
from devops.cpp.ast.registry import ALL_CHECKS, configure_checks, select_checks
from devops.logger import cpp_check_logger
from devops.rules import (
    FileRuleInput,
    ResultType,
    ResultTypeEnum,
    Rule,
    RuleInputType,
    RuleType,
)

DEFAULT_COMPILE_ARGS = ["-std=c++23"]


# Flags that are not useful to libclang and whose following argument (if any)
# should also be dropped. -include / -include-pch are handled separately (see
# _consume_include) since whether to keep them depends on the file they name.
_SKIP_WITH_ARG = frozenset(("-o", "-MF", "-MT", "-MQ"))
# Flags that are not useful but take no following argument.
_SKIP_ALONE = frozenset(
    (
        "-c",
        # Turn-error-into-error flags: too strict for static analysis where we
        # only care about AST structure, not compilation correctness.
        "-Werror",
        "-pedantic-errors",
    )
)
# Source / header file extensions to skip when they appear as positional args.
_SOURCE_EXTENSIONS = (".cpp", ".cxx", ".cc", ".c", ".hpp", ".hxx", ".hh", ".h")
# -include / -include-pch: force-include another file before the translation
# unit proper. CMake's target_precompile_headers() emits both for the same
# PCH, spelled differently per compiler/wrapping (see _consume_include).
_INCLUDE_FLAGS = frozenset(("-include", "-include-pch"))


def _include_file_exists(file_arg: str | None) -> bool:
    """Check whether an ``-include``'s file argument names a real file."""
    if not file_arg:
        return False
    try:
        return Path(file_arg).is_file()
    except OSError:
        return False


def _consume_include(it: typing.Iterator[str], result: list[str], flag: str) -> None:
    """Handle the file argument of an already-consumed ``-include``/``-include-pch``.

    ``-include-pch`` (the compiled PCH binary) is always dropped together
    with its file argument: it's serialized by whichever real compiler
    produced it and is generally incompatible with pip's bundled libclang,
    triggering a hard parse failure regardless of whether the file exists.

    A plain ``-include <file>`` (the textual PCH header CMake also
    generates alongside the binary one) is kept — normalized to a bare
    pair regardless of how it was originally wrapped — when that file
    exists on disk: project headers often rely on it being force-included
    first for standard-library symbols (``<optional>``, ``<format>``, ...)
    they don't include themselves, so dropping it unconditionally produces
    a cascade of unrelated "no member"/"too many errors" failures. It's
    dropped, like ``-include-pch``, when the file is missing (e.g. a
    fresh/partial checkout), to avoid a "file not found" fatal error.

    The file argument may itself be wrapped in another ``-Xclang``
    (``-Xclang -include(-pch) -Xclang <file>``) or bare
    (``-Xclang -include(-pch) <file>`` / plain ``-include(-pch) <file>``)
    depending on the CMake/Clang version, so this peeks one token rather
    than assuming a fixed shape.

    Parameters
    ----------
    it: typing.Iterator[str]
        The shared argument iterator, positioned right after the flag.
    result: list[str]
        The filtered-args list being built; appended to in place.
    flag: str
        Either ``"-include"`` or ``"-include-pch"``.

    """
    following = next(it, None)  # the file, bare or another -Xclang
    file_arg = next(it, None) if following == "-Xclang" else following
    if flag == "-include" and file_arg is not None and _include_file_exists(file_arg):
        result.append("-include")
        result.append(file_arg)


def _consume_xclang(it: typing.Iterator[str], result: list[str]) -> None:
    """Handle the token(s) after an ``-Xclang`` already consumed from `it`.

    Delegates ``-Xclang -include(-pch) ...`` to `_consume_include`. Every
    other ``-Xclang <frontend-arg>`` pair is appended to `result` as-is.

    Parameters
    ----------
    it: typing.Iterator[str]
        The shared argument iterator, positioned right after ``-Xclang``.
    result: list[str]
        The filtered-args list being built; appended to in place.

    """
    xclang_arg = next(it, None)
    if xclang_arg in _INCLUDE_FLAGS:
        _consume_include(it, result, xclang_arg)
        return
    if xclang_arg is not None:
        result.append("-Xclang")
        result.append(xclang_arg)


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
        if arg in _INCLUDE_FLAGS:
            _consume_include(it, result, arg)
            continue
        if arg == "-Xclang":
            _consume_xclang(it, result)
            continue
        result.append(arg)
    # Clang/libclang compatibility: silently ignore GCC-only flags that
    # would otherwise cause libclang to reject the translation unit.
    result += ["-Wno-unknown-warning-option", "-Wno-unused-command-line-argument"]

    return _with_auto_resource_dir(result, raw[0])


@dataclass
class ASTWorkerSpec:
    """Picklable snapshot of `ASTChecksRule`'s constructor args.

    Sent to a `ProcessPoolExecutor` worker so it can build its own
    `ASTChecksRule` locally (fresh `Check` instances, its own
    `clang.CompilationDatabase`), since the rule instance itself holds
    unpicklable libclang/ctypes objects.
    """

    compile_args: list[str] | None
    compile_commands_db: str | None
    enabled_check_ids: list[str] | None
    disabled_check_ids: list[str] | None
    check_config: dict[str, dict] | None


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
        self._worker_spec = ASTWorkerSpec(
            compile_args=compile_args,
            compile_commands_db=compile_commands_db,
            enabled_check_ids=enabled_check_ids,
            disabled_check_ids=disabled_check_ids,
            check_config=check_config,
        )
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

    def check_file(self, path: Path, content: str) -> ResultType:
        """Run all enabled AST checks against a single file's content.

        Public equivalent of `_run`, usable directly (without constructing
        a `FileRuleInput`) by callers like the process-pool worker in
        `run_ast_checks_in_worker`.

        Parameters
        ----------
        path: Path
            The file being checked.
        content: str
            The file's full content.

        Returns
        -------
        ResultType
            Same as `_run`.

        """
        return self._run(FileRuleInput(file_content=content, path=path))

    def finalize_run(self) -> bool:
        """Call global_finalize() on every active check after all files are done.

        Returns
        -------
        bool
            True if all checks passed, False if any check reported an error.

        """
        return all(check.global_finalize() for check in self.checks)

    def worker_spec(self) -> ASTWorkerSpec:
        """Return a picklable spec that can rebuild an equivalent instance.

        Used by `devops.cpp.checks` to run this rule's checks across a
        `ProcessPoolExecutor`: the spec (not this instance, which holds
        unpicklable libclang objects) is sent to each worker, which calls
        `ASTChecksRule.from_spec` to build its own local instance.

        Returns
        -------
        ASTWorkerSpec
            The constructor args this instance was built with.

        """
        return self._worker_spec

    @classmethod
    def from_spec(cls, spec: ASTWorkerSpec) -> ASTChecksRule:
        """Build a fresh `ASTChecksRule` from a previously captured spec.

        Parameters
        ----------
        spec: ASTWorkerSpec
            As returned by another instance's `worker_spec()`.

        Returns
        -------
        ASTChecksRule
            A new, independently-constructed instance with the same
            configuration (fresh `Check` instances, its own
            `clang.CompilationDatabase`).

        """
        return cls(
            compile_args=spec.compile_args,
            compile_commands_db=spec.compile_commands_db,
            enabled_check_ids=spec.enabled_check_ids,
            disabled_check_ids=spec.disabled_check_ids,
            check_config=spec.check_config,
        )

    def collect_state(self) -> dict[str, dict]:
        """Return every check's exportable cross-file state, keyed by check id.

        Returns
        -------
        dict[str, dict]
            ``{check.id: check.collect_state()}`` for each active check.

        """
        return {check.id: check.collect_state() for check in self.checks}

    def merge_state(self, states: dict[str, dict]) -> None:
        """Merge a `collect_state()` snapshot from another instance.

        Parameters
        ----------
        states: dict[str, dict]
            A snapshot as returned by another instance's `collect_state`.

        """
        for check in self.checks:
            if check.id in states:
                check.merge_state(states[check.id])


# Module-level so a ProcessPoolExecutor can pickle a reference to it (not a
# bound method or closure). Each worker process builds its own ASTChecksRule
# once via the initializer below and reuses it across every file it checks,
# so a check's cross-file state (e.g. EnforceParamNameForType) accumulates
# correctly for that worker's share of the files.
_worker_rule: ASTChecksRule | None = None


def _init_ast_worker(spec: ASTWorkerSpec) -> None:
    """Build this worker process's local `ASTChecksRule` from `spec`.

    Parameters
    ----------
    spec: ASTWorkerSpec
        As returned by the main process's `ASTChecksRule.worker_spec()`.

    """
    global _worker_rule  # noqa: PLW0603 - required ProcessPoolExecutor initializer pattern
    _worker_rule = ASTChecksRule.from_spec(spec)


def run_ast_checks_in_worker(
    path: Path, content: str
) -> tuple[ResultType, dict[str, dict]]:
    """Check one file against this worker's local `ASTChecksRule`.

    Parameters
    ----------
    path: Path
        The file to check.
    content: str
        The file's full content (read once by the main process and sent
        here, rather than re-read from disk in the worker).

    Returns
    -------
    tuple[ResultType, dict[str, dict]]
        The check result, and a `collect_state()` snapshot of this worker's
        checks for the main process to merge back after every file (state
        only grows, so merging the snapshot from every call, not just the
        last, is safe and gives the correct union across all workers).

    """
    if _worker_rule is None:
        msg = "AST worker process was not initialized with _init_ast_worker"
        raise RuntimeError(msg)
    result = _worker_rule.check_file(path, content)
    return result, _worker_rule.collect_state()
