"""C++ checks module."""

from pathlib import Path

from devops import __GLOBAL_CONFIG__
from devops.config import CppConfig
from devops.cpp.state import (
    any_failed,
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


class CppCheckError(Exception):
    """Custom exception for C++ check errors."""


def run_line_checks(rules: list[Rule], file: Path) -> list[ResultType]:
    """Run line-based C++ checks on a given file.

    Parameters
    ----------
    rules: list[Rule]
        The list of rules to apply.
    file: Path
        The file to check.

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

    with open_file(file, mode="r") as f:
        for line in f:
            for rule in rules:
                if file_type not in rule.file_types:
                    continue

                results.append(rule.apply(line))

    return results


def run_file_rules(rules: list[Rule], file: Path) -> list[ResultType]:
    """Run file-based C++ checks on a given file.

    Parameters
    ----------
    rules: list[Rule]
        The list of rules to apply.
    file: Path
        The file to check.

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


def _check_single_file(
    file_rules: list[Rule],
    line_rules: list[Rule],
    filename: Path,
) -> bool:
    """Run all rules on one file, log failures, return True if all passed."""
    file_results = run_file_rules(file_rules, filename)
    file_results += run_line_checks(line_rules, filename)
    file_passed = all(result.value == ResultTypeEnum.Ok for result in file_results)
    if not file_passed:
        for res in file_results:
            if res.value != ResultTypeEnum.Ok:
                cpp_check_logger.error(
                    f"CPP check error: result in {filename}: {res.description}"
                )
    return file_passed


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
) -> bool:
    """Run C++ checks based on the provided rules.

    By default the function returns immediately after encountering the first
    file with errors (fail-fast).  Set ``config.fail_fast = False`` (or pass
    ``--no-fail-fast`` on the CLI) to check all files regardless.

    When ``state_file`` is given the run is *incremental*: results are
    persisted to ``state_file`` after every checked file, and only files
    that are new, previously failed, or modified since the last run are
    re-checked.  The return value is ``False`` whenever any entry in the
    accumulated state is failed.

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
        state = load_state(state_file)
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
    total = len(files)
    passed = True

    try:
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
    finally:
        passed = _finalize_run(state_file, state, rules, passed=passed)

    return passed
