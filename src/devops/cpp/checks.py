"""C++ checks module."""

from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from devops import __GLOBAL_CONFIG__
from devops.config import CppConfig
from devops.cpp.state import (
    any_failed,
    compute_config_hash,
    filter_incremental,
    load_state,
    save_state,
    update_entry,
)
from devops.files import (
    FileType,
    determine_file_type,
    get_changed_files,
    get_dirs_in_dir,
    get_files_in_dirs,
    get_staged_files,
    open_file,
)
from devops.logger import cpp_check_logger
from devops.rules import (
    FileRuleInput,
    ResultType,
    Rule,
    filter_file_rules,
    filter_line_rules,
    is_file_rule,
    is_line_rule,
)
from devops.rules.result_type import ResultTypeEnum

try:
    from devops.cpp.ast.rule import (
        ASTChecksRule,
        _init_ast_worker,
        run_ast_checks_in_worker,
    )
except ImportError:
    ASTChecksRule = None


class CppCheckError(Exception):
    """Custom exception for C++ check errors."""


def run_line_checks(
    rules: list[Rule], file: Path, content: str | None = None
) -> list[ResultType]:
    """Run line-based C++ checks on a given file.

    Parameters
    ----------
    rules: list[Rule]
        The list of rules to apply.
    file: Path
        The file to check.
    content: str | None
        The file's full content, if already read by the caller. When
        ``None`` (the default), the file is read from disk.

    Returns
    -------
    list[ResultType]
        The list of results from the checks.

    Raises
    ------
    CppCheckError
        If a non-line rule is provided.

    """
    results = []
    file_type = determine_file_type(file)

    if any(not is_line_rule(rule) for rule in rules):
        msg = "Non-line rule provided to run_line_checks"
        raise CppCheckError(msg)

    if content is None:
        with open_file(file, mode="r") as f:
            content = f.read()

    for line in content.splitlines(keepends=True):
        for rule in rules:
            if file_type not in rule.file_types:
                continue

            results.append(rule.apply(line))

    return results


def run_file_rules(
    rules: list[Rule], file: Path, content: str | None = None
) -> list[ResultType]:
    """Run file-based C++ checks on a given file.

    Parameters
    ----------
    rules: list[Rule]
        The list of rules to apply.
    file: Path
        The file to check.
    content: str | None
        The file's full content, if already read by the caller. When
        ``None`` (the default), the file is read from disk.

    Returns
    -------
    list[ResultType]
        The list of results from the checks.

    Raises
    ------
    CppCheckError
        If a non-file rule is provided.

    """
    results = []
    file = Path(file)  # to be 100% sure
    file_type = determine_file_type(file)

    if any(not is_file_rule(rule) for rule in rules):
        msg = "Non-file rule provided to run_file_rules"
        raise CppCheckError(msg)

    if content is None:
        with open_file(file, mode="r") as f:
            content = f.read()

    for rule in rules:
        if file_type not in rule.file_types:
            continue

        results.append(rule.apply(FileRuleInput(file_content=content, path=file)))

    return results


def _is_excluded(path: Path, exclude: list[str]) -> bool:
    """Return True if any directory component of ``path`` is excluded."""
    return any(part in exclude for part in path.parts[:-1])


def _collect_changed_files(
    base_ref: str, dirs: list[Path] | None, exclude: list[str]
) -> list[Path]:
    """Collect files changed since ``base_ref``, honoring dirs and exclude_dirs."""
    cpp_check_logger.info(f"Running checks on files changed since '{base_ref}'...")
    changed = [f for f in get_changed_files(base_ref) if not _is_excluded(f, exclude)]
    if dirs is None:
        return changed
    resolved_dirs = [d.resolve() for d in dirs]
    return [f for f in changed if any(d in f.resolve().parents for d in resolved_dirs)]


def _collect_cpp_files(
    config: CppConfig, dirs: list[Path] | None, base_ref: str | None = None
) -> list[Path]:
    """Collect candidate C++ files according to config, CLI dirs and base ref."""
    exclude = config.exclude_dirs or []

    if base_ref is not None:
        return _collect_changed_files(base_ref, dirs, exclude)

    if dirs is not None:
        cpp_check_logger.info(
            f"Running checks in directories: {[str(d) for d in dirs]}"
        )
        return get_files_in_dirs(dirs, exclude_dirs=exclude)

    if config.check_only_staged_files:
        cpp_check_logger.info("Running checks on staged files...")
        return get_staged_files()

    if config.check_dirs:
        resolved: list[Path] = []
        for pattern in config.check_dirs:
            matches = [m for m in Path().glob(pattern) if m.is_dir()]
            if not matches:
                cpp_check_logger.warning(
                    f"check_dirs: pattern '{pattern}' matched no directories"
                )
            resolved.extend(matches)
        cpp_check_logger.info(
            f"Running checks in configured directories: {[str(d) for d in resolved]}"
        )
        return get_files_in_dirs(resolved, exclude_dirs=exclude)

    cpp_check_logger.info("Running full checks...")
    all_dirs = get_dirs_in_dir()
    cpp_check_logger.debug(f"Checking directories: {[str(d) for d in all_dirs]}")
    return get_files_in_dirs(all_dirs, exclude_dirs=exclude)


def _read_file_content(file: Path) -> str:
    """Read a file's full content as text."""
    with open_file(file, mode="r") as f:
        return f.read()


def _evaluate_results(filename: Path, results: list[ResultType]) -> bool:
    """Log every failing result for ``filename``; return True if all passed."""
    file_passed = all(result.value == ResultTypeEnum.Ok for result in results)
    if not file_passed:
        for res in results:
            if res.value != ResultTypeEnum.Ok:
                cpp_check_logger.error(
                    f"CPP check error: result in {filename}: {res.description}"
                )
    return file_passed


def _check_single_file(
    file_rules: list[Rule],
    line_rules: list[Rule],
    filename: Path,
) -> bool:
    """Run all rules on one file, log failures, return True if all passed."""
    content = _read_file_content(filename)
    file_results = run_file_rules(file_rules, filename, content=content)
    file_results += run_line_checks(line_rules, filename, content=content)
    return _evaluate_results(filename, file_results)


def _find_ast_rule(file_rules: list[Rule]) -> Rule | None:
    """Return the `ASTChecksRule` in ``file_rules``, if any.

    Used to split off the one CPU-heavy rule type (libclang AST checks) so
    it alone can run across a process pool, while every other (cheap)
    file/line rule keeps running serially in the main process.
    """
    if ASTChecksRule is None:
        return None
    return next((r for r in file_rules if isinstance(r, ASTChecksRule)), None)


def _run_checks_serial(
    file_rules: list[Rule],
    line_rules: list[Rule],
    files: list[Path],
    config: CppConfig,
    state: dict[str, dict],
    state_file: Path | None,
) -> bool:
    """Run checks for ``files`` one at a time, stopping at the first failure.

    Identical to the pre-parallelism behavior: used whenever
    ``config.parallel_jobs == 1`` (the default).
    """
    total = len(files)
    passed = True
    for i, filename in enumerate(files, start=1):
        cpp_check_logger.info(f"({i}/{total}) {filename}")
        file_passed = _check_single_file(file_rules, line_rules, filename)
        if not file_passed:
            passed = False
            if state_file is not None:
                update_entry(state, filename, passed=False)
            if config.fail_fast:
                break
        elif state_file is not None:
            update_entry(state, filename, passed=True)
    return passed


def _run_checks_parallel(
    file_rules: list[Rule],
    line_rules: list[Rule],
    files: list[Path],
    config: CppConfig,
    state: dict[str, dict],
    state_file: Path | None,
) -> bool:
    """Run checks for ``files``, parallelizing the AST-check portion.

    The libclang parse behind `ASTChecksRule` is the one CPU-bound,
    per-file-independent cost worth parallelizing; everything else (line
    rules, the license header check, style rules) is cheap string/regex
    work. So only the AST rule, if present, is dispatched across a
    `ProcessPoolExecutor` (threads do not help here: libclang's ctypes
    binding does not release the GIL during the parse, measured to make
    threaded parsing strictly slower than serial). Every other file/line
    rule still runs once per file, serially, in the main process — exactly
    as in `_check_single_file`.

    When there is no `ASTChecksRule` in ``file_rules`` (AST checks are
    disabled, or the caller supplied its own custom rules), there is
    nothing to gain from parallelism here, so this falls back to
    `_run_checks_serial`.

    Files are submitted to the process pool in batches of
    ``config.parallel_jobs`` (or ``os.cpu_count()`` when
    ``parallel_jobs <= 0``). When ``config.fail_fast`` is True, scheduling
    of further batches stops as soon as a failure is seen in the current
    in-flight batch: fail-fast no longer guarantees stopping at the *exact*
    first failing file in listing order, only "soon after" a failure.
    """
    ast_rule = _find_ast_rule(file_rules)
    if ast_rule is None:
        return _run_checks_serial(
            file_rules, line_rules, files, config, state, state_file
        )

    other_file_rules = [r for r in file_rules if r is not ast_rule]
    total = len(files)
    max_workers = config.parallel_jobs if config.parallel_jobs > 0 else None
    batch_size = max_workers or total
    passed = True
    checked = 0

    with ProcessPoolExecutor(
        max_workers=max_workers,
        initializer=_init_ast_worker,
        initargs=(ast_rule.worker_spec(),),
    ) as executor:
        for start in range(0, total, batch_size):
            batch = files[start : start + batch_size]
            contents = {f: _read_file_content(f) for f in batch}
            future_to_file = {
                executor.submit(run_ast_checks_in_worker, f, contents[f]): f
                for f in batch
            }
            batch_failed = False
            for future, filename in future_to_file.items():
                ast_result, worker_state = future.result()
                ast_rule.merge_state(worker_state)

                content = contents[filename]
                file_results = run_file_rules(
                    other_file_rules, filename, content=content
                )
                file_results += run_line_checks(line_rules, filename, content=content)
                file_results.append(ast_result)

                checked += 1
                cpp_check_logger.info(f"({checked}/{total}) {filename}")
                file_passed = _evaluate_results(filename, file_results)
                if not file_passed:
                    passed = False
                    batch_failed = True
                    if state_file is not None:
                        update_entry(state, filename, passed=False)
                elif state_file is not None:
                    update_entry(state, filename, passed=True)
            if batch_failed and config.fail_fast:
                break

    return passed


def _finalize_run(
    state_file: Path | None,
    state: dict[str, dict],
    rules: list[Rule],
    *,
    passed: bool,
) -> bool:
    """Persist state and call global finalizers; returns overall pass/fail."""
    if state_file is not None:
        save_state(state_file, state)
        if any_failed(state):
            passed = False
    return passed and all(rule.finalize_run() for rule in rules)


def run_cpp_checks(
    rules: list[Rule],
    config: CppConfig = __GLOBAL_CONFIG__.cpp,
    dirs: list[Path] | None = None,
    state_file: Path | None = None,
    base_ref: str | None = None,
    config_file: Path | None = None,
) -> bool:
    """Run C++ checks based on the provided rules.

    By default the function returns immediately after encountering the first
    file with errors (fail-fast).  Set ``config.fail_fast = False`` (or pass
    ``--no-fail-fast`` on the CLI) to check all files regardless.

    When ``state_file`` is given the run is *incremental*: results are
    persisted to ``state_file`` after every checked file, and only files
    that are new, previously failed, or modified since the last run are
    re-checked.  The return value is ``False`` whenever any entry in the
    accumulated state is failed.  The state is discarded whenever
    ``config_file`` changed since it was written.

    When ``config.parallel_jobs != 1`` and an AST-checks rule is present,
    the libclang parse (the one CPU-bound, per-file cost) is dispatched
    across a process pool instead of running serially; every other rule
    (line/file/style rules) still runs once per file in the main process,
    since that work is cheap. With ``parallel_jobs > 1`` and ``fail_fast``
    enabled, the run stops scheduling further files soon after a failure is
    seen, rather than at the exact first failing file in listing order.

    Parameters
    ----------
    rules: list[Rule]
        The list of rules to apply.
    config: CppConfig
        The global C++ configuration.
    dirs: list[Path] | None
        If given, only files under these directories are checked.
    state_file: Path | None
        Path to the JSON state file used for incremental runs.  When
        ``None`` (the default) no state is read or written and the classic
        fail-fast behavior is used.
    base_ref: str | None
        A git commit hash or branch name.  When given, only files changed
        relative to it (see ``get_changed_files``) are checked, overriding
        ``check_only_staged_files`` and ``check_dirs``.  ``dirs`` further
        restricts the changed files when also given.
    config_file: Path | None
        The TOML config file in use.  Its content hash is stored in the state
        file; when it differs on the next run, all incremental state is
        invalidated and every file is re-checked.

    Raises
    ------
    CppCheckError
        If invalid (non-file or non-line) rules are provided.
    GitRefError
        If ``base_ref`` cannot be resolved.

    Returns
    -------
    bool
        True if all checks pass, False if any check fails.

    """
    raw_files = _collect_cpp_files(config, dirs, base_ref)
    files = [f for f in raw_files if FileType.is_cpp_type(determine_file_type(f))]

    if not files:
        cpp_check_logger.warning("No files to check.")
        return True

    state: dict[str, dict] = {}
    if state_file is not None:
        state = load_state(state_file, compute_config_hash(config_file))
        to_check = filter_incremental(files, state)
        skipped = len(files) - len(to_check)
        if skipped:
            cpp_check_logger.info(
                f"Incremental: skipping {skipped} unchanged passing file(s)."
            )
        files = to_check

    if not files:
        cpp_check_logger.info(
            "Incremental: all files already passed — nothing to check."
        )
        return not any_failed(state)

    file_rules = filter_file_rules(rules)
    line_rules = filter_line_rules(rules)
    passed = True

    try:
        if config.parallel_jobs == 1:
            passed = _run_checks_serial(
                file_rules, line_rules, files, config, state, state_file
            )
        else:
            passed = _run_checks_parallel(
                file_rules, line_rules, files, config, state, state_file
            )
    finally:
        passed = _finalize_run(state_file, state, rules, passed=passed)

    return passed
