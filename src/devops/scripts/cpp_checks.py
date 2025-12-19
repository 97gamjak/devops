"""Module defining C++ check rules."""

import sys
from pathlib import Path

from devops.cpp import cpp_rules
from devops.files import (
    __EXECUTION_DIR__,
    determine_file_type,
    get_files_in_dirs,
    get_staged_files,
)
from devops.logger import cpp_check_logger
from devops.rules import ResultType, ResultTypeEnum, Rule, filter_line_rules

__CPP_DIRS__ = ["include", "test"]
__OTHER_DIRS__ = ["scripts"]
__EXCLUDE_DIRS__ = ["__pycache__", ".ruff_cache"]
__EXCLUDE_FILES__ = [".gitignore"]

__DIRS__ = __CPP_DIRS__ + __OTHER_DIRS__


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

    """
    results = []
    file_type = determine_file_type(file)

    with Path(file).open("r", encoding="utf-8") as f:
        line_rules = filter_line_rules(rules)
        for line in f:
            for rule in line_rules:
                if file_type not in rule.file_types:
                    continue

                results.append(rule.apply(line))

    return results


def run_checks(rules: list[Rule]) -> None:
    """Run C++ checks based on the provided rules.

    Returns immediately after encountering the first file with errors.

    Parameters
    ----------
    rules: list[Rule]
        The list of rules to apply.

    """
    if "full" in sys.argv:
        cpp_check_logger.info("Running full checks...")
        cpp_check_logger.debug(f"Checking directories: {__DIRS__}")
        dirs = [__EXECUTION_DIR__ / dir_name for dir_name in __DIRS__]
        files = get_files_in_dirs(dirs, __EXCLUDE_DIRS__, __EXCLUDE_FILES__)
    else:
        cpp_check_logger.info("Running checks on staged files...")
        files = get_staged_files()

    if not files:
        cpp_check_logger.warning("No files to check.")
        return

    for filename in files:
        cpp_check_logger.debug(f"Checking file: {filename}")
        file_results = run_line_checks(rules, filename)
        if any(result.value != ResultTypeEnum.Ok for result in file_results):
            filtered_results = [
                res for res in file_results if res.value != ResultTypeEnum.Ok
            ]
            for res in filtered_results:
                cpp_check_logger.error(
                    f"Line check result in {filename}: {res.description}"
                )
            return


def main() -> None:
    """Run C++ checks."""
    run_checks(cpp_rules)
