"""C++ checks module."""

from pathlib import Path

from devops import __GLOBAL_CONFIG__
from devops.config import CppConfig
from devops.files import (
    FileType,
    determine_file_type,
    get_files_in_dirs,
    get_staged_files,
)
from devops.logger import cpp_check_logger
from devops.rules import (
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

    with Path(file).open("r", encoding="utf-8") as f:
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

    """
    results = []
    file_type = determine_file_type(file)

    if any(not is_file_rule(rule) for rule in rules):
        msg = "Non-file rule provided to run_file_rules"
        raise CppCheckError(msg)

    with Path(file).open("r", encoding="utf-8") as f:
        content = f.read()
        for rule in rules:
            if file_type not in rule.file_types:
                continue

            results.append(rule.apply((content,)))

    return results


def run_cpp_checks(
    rules: list[Rule], config: CppConfig = __GLOBAL_CONFIG__.cpp
) -> None:
    """Run C++ checks based on the provided rules.

    Returns immediately after encountering the first file with errors.

    Parameters
    ----------
    rules: list[Rule]
        The list of rules to apply.
    config: CppConfig
        The global C++ configuration.

    Raises
    ------
    CppCheckError
        If there are errors found during the checks.

    """
    if config.check_only_staged_files:
        cpp_check_logger.info("Running checks on staged files...")
        files = get_staged_files()
    else:
        cpp_check_logger.info("Running full checks...")

        cwd = Path().cwd()
        dirs = [path.relative_to(cwd) for path in cwd.iterdir() if path.is_dir()]
        files = get_files_in_dirs(dirs)

        cpp_check_logger.debug(f"Checking directories: {[str(d) for d in dirs]}")

    files = [file for file in files if FileType.is_cpp_type(determine_file_type(file))]

    if not files:
        cpp_check_logger.warning("No files to check.")
        return

    file_rules = filter_file_rules(rules)
    line_rules = filter_line_rules(rules)

    for filename in files:
        cpp_check_logger.debug(f"Checking file: {filename}")

        # file rules
        file_results = run_file_rules(file_rules, filename)

        # line rules
        file_results += run_line_checks(line_rules, filename)

        if any(result.value != ResultTypeEnum.Ok for result in file_results):
            filtered_results = [
                res for res in file_results if res.value != ResultTypeEnum.Ok
            ]
            for res in filtered_results:
                cpp_check_logger.error(
                    f"CPP check error: result in {filename}: {res.description}"
                )
            return
