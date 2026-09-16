"""Module defining C++ check rules."""

import sys
from dataclasses import replace
from pathlib import Path

import typer

from devops import __GLOBAL_CONFIG__
from devops.cpp import build_cpp_rules, run_cpp_checks
from devops.utils import mstd_print

app = typer.Typer(help="C++ code quality checks.")


@app.command()
def cpp_checks(
    license_header: str | None = None,
    dirs: list[str] | None = None,
    files: list[str] | None = None,
) -> None:
    """Run C++ code quality checks.

    Parameters
    ----------
    license_header: str | None
        The path to the license header file. If None, uses the global configuration.
    dirs: list[str] | None
        List of directories to check.
        If None, uses all directories in the current directory.
    files: list[str] | None
        List of specific files to check. When given, directory scanning is
        skipped entirely. Useful for re-running checks on a known set of
        files (e.g. only those that failed in a previous run).

    """
    if license_header is None:
        license_header = __GLOBAL_CONFIG__.cpp.license_header

    config = replace(
        __GLOBAL_CONFIG__.cpp,
        license_header=license_header,
    )

    cli_dirs = [Path(d) for d in dirs] if dirs is not None else None
    cli_files = [Path(f) for f in files] if files is not None else None

    rules = build_cpp_rules(config)
    passed = run_cpp_checks(rules, config, dirs=cli_dirs, files=cli_files)

    if not passed:
        mstd_print("C++ checks failed.")
        sys.exit(1)
