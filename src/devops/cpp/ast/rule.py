"""Rule adapter exposing the AST-check engine through devops's Rule interface."""

from __future__ import annotations

import os
import typing
from dataclasses import dataclass
from pathlib import Path

import clang.cindex as clang

from devops.cpp.ast.engine import (
    _HEADER_SUFFIXES,
    _with_auto_resource_dir,
    run_ast_checks,
)
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


def _filter_compile_args(raw: list[str]) -> list[str]:
    """Turn a raw compile command (compiler first) into libclang-friendly args.

    Parameters
    ----------
    raw: list[str]
        The full argv of a compile command; ``raw[0]`` is the compiler.

    Returns
    -------
    list[str]
        The flags to hand to libclang (no compiler, output, dependency or
        positional source arguments), with an auto-detected ``-resource-dir``
        for the compiler appended where possible.

    """
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


def _args_from_compile_commands(
    db: clang.CompilationDatabase, path: Path
) -> list[str] | None:
    """Return filtered compile args for *path* from *db*, or None if not found."""
    cmds = db.getCompileCommands(str(path.resolve()))
    if not cmds:
        return None
    return _filter_compile_args(list(cmds[0].arguments))


# Flags that put a directory on the include search path, in both the joined
# (``-Idir``) and separated (``-I dir``) spelling.
_INCLUDE_DIR_FLAGS = ("-I", "-isystem", "-iquote", "-idirafter")


def _include_dirs(raw: list[str], directory: str) -> tuple[Path, ...]:
    """Collect the include search directories named in a raw compile command.

    Parameters
    ----------
    raw: list[str]
        The full argv of a compile command.
    directory: str
        The command's working directory; relative include dirs are resolved
        against it.

    Returns
    -------
    tuple[Path, ...]
        Absolute, de-duplicated include directories, in command-line order.

    """
    dirs: dict[Path, None] = {}
    it = iter(raw[1:])
    for arg in it:
        value: str | None = None
        for flag in _INCLUDE_DIR_FLAGS:
            if arg == flag:
                value = next(it, None)
                break
            if arg.startswith(flag) and flag == "-I":
                value = arg[len(flag) :]
                break
        if value:
            dirs[Path(os.path.normpath(Path(directory) / value))] = None
    return tuple(dirs)


@dataclass(frozen=True)
class _CompileEntry:
    """One compile-database entry reduced to what header lookup needs."""

    file: str
    raw: tuple[str, ...]
    include_dirs: tuple[Path, ...]


def _load_entries(db: clang.CompilationDatabase) -> list[_CompileEntry]:
    """Read every entry of *db* once, sorted by file for deterministic lookup."""
    entries = []
    for cmd in db.getAllCompileCommands():
        raw = list(cmd.arguments)
        entries.append(
            _CompileEntry(
                file=os.path.normpath(Path(cmd.directory) / cmd.filename),
                raw=tuple(raw),
                include_dirs=_include_dirs(raw, cmd.directory),
            )
        )
    return sorted(entries, key=lambda e: e.file)


def _best_explicit_match(
    entries: list[_CompileEntry], header: Path
) -> _CompileEntry | None:
    """Return the entry whose declared ``-I``/``-isystem`` path best reaches *header*.

    The most specific matching directory wins. Several TUs often tie on that
    specificity (e.g. many test ``.cpp`` files all have the same shared
    test-fixture directory on their path), so ties are broken by preferring,
    first, a TU whose own filename stem matches the header's — the common
    ``testFoo.hpp`` / ``testFoo.cpp`` pairing, where that TU is the one
    actually written to exercise the header, rather than a sibling that
    merely happens to share the fixture directory — and otherwise by
    preferring the TU with the most include directories overall, the one
    least likely to be missing something the header needs. Remaining ties
    fall back to file name (via `entries` already being sorted), so the
    result stays deterministic.
    """
    best: _CompileEntry | None = None
    best_depth = -1
    best_stem_match = False
    best_breadth = -1
    header_stem = header.stem
    for entry in entries:
        for inc in entry.include_dirs:
            if not header.is_relative_to(inc):
                continue
            depth = len(inc.parts)
            stem_match = Path(entry.file).stem == header_stem
            breadth = len(entry.include_dirs)
            better = depth > best_depth or (
                depth == best_depth
                and (
                    (stem_match and not best_stem_match)
                    or (stem_match == best_stem_match and breadth > best_breadth)
                )
            )
            if better:
                best, best_depth, best_stem_match, best_breadth = (
                    entry,
                    depth,
                    stem_match,
                    breadth,
                )
    return best


def _best_same_dir_match(
    entries: list[_CompileEntry], header: Path
) -> _CompileEntry | None:
    """Return the richest entry whose own source file sits next to *header*.

    A compiler always searches a quote-included file's own directory first,
    with no ``-I`` needed for it — so a header that merely sits beside its
    ``.cpp`` (e.g. in ``benchmarks/perf`` or a ``src/`` subtree that mirrors
    no ``include/`` root) is reachable from that TU even though the
    directory never appears as an explicit ``-I``. This is only consulted
    when no entry's *explicit* include path reaches the header
    (`_best_explicit_match` returned None): unlike an explicit ``-I``, "sits
    in the same folder" is true of every sibling file, so it is too weak a
    signal to let it outrank a genuine, intentional ``-I`` match.
    """
    same_dir = [e for e in entries if Path(e.file).parent == header.parent]
    if not same_dir:
        return None
    return max(same_dir, key=lambda e: len(e.include_dirs))


def _args_for_header(entries: list[_CompileEntry], header: Path) -> list[str] | None:
    """Return compile args for a header, taken from a TU that can reach it.

    A header has no compile command of its own: it is always compiled as part
    of some translation unit, with that unit's flags. The unit's include
    search path decides which headers it can reach, so a unit that has one of
    the header's parent directories on its ``-I`` / ``-isystem`` path is, by
    the compiler's own lookup rules, one that can include it — see
    `_best_explicit_match` for how the most specific such directory is
    chosen. Failing that, `_best_same_dir_match` falls back to a TU whose own
    source file merely sits beside the header, for the common case of a
    header with no ``include/``-rooted directory on any TU's path at all
    (e.g. one living next to its ``.cpp`` under ``benchmarks/`` or ``src/``).

    This deliberately does not use ``CompilationDatabase.getCompileCommands``
    for headers: libclang answers that call for files missing from the
    database with a *guessed* command borrowed from the entry with the most
    similar path (the same heuristic clangd uses), never with "not found". For
    a header whose include tree does not mirror the source tree, that guess
    is an unrelated unit lacking the header's dependencies.

    Parameters
    ----------
    entries: list[_CompileEntry]
        Entries as returned by `_load_entries`.
    header: Path
        The header being checked.

    Returns
    -------
    list[str] | None
        Filtered compile args of the chosen unit, or None if no unit can
        reach *header*.

    """
    header = header.resolve()
    for entry in entries:
        if entry.file == str(header):  # a real entry for the header itself
            return _filter_compile_args(list(entry.raw))

    best = _best_explicit_match(entries, header) or _best_same_dir_match(
        entries, header
    )
    if best is None:
        return None
    cpp_check_logger.debug(
        f"AST checks: '{header}' has no compile command — using the flags of "
        f"'{best.file}', which can reach it."
    )
    return _filter_compile_args(list(best.raw))


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
        self._entries: list[_CompileEntry] | None = None  # loaded on first header
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
            path = file_rule_input.path
            if path.suffix.lower() in _HEADER_SUFFIXES:
                if self._entries is None:
                    self._entries = _load_entries(self._compile_db)
                per_file = _args_for_header(self._entries, path)
            else:
                per_file = _args_from_compile_commands(self._compile_db, path)
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
