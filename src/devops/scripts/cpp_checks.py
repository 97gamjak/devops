"""Module defining C++ check rules."""

from dataclasses import replace
from pathlib import Path

import typer

from devops import __GLOBAL_CONFIG__
from devops.cpp import build_cpp_rules, run_cpp_checks
from devops.files import filter_cpp_files, get_dirs_in_dir, get_files_in_dirs

app = typer.Typer(help="C++ code quality checks.")


@app.command()
def cpp_checks(
    license_header: str | None = None, dirs: list[str] | None = None
) -> None:
    """Run C++ code quality checks.

    Parameters
    ----------
    license_header: str | None
        The path to the license header file. If None, uses the global configuration.
    dirs: list[str] | None
        List of directories to check.
        If None, uses all directories in the current directory.

    """
    if license_header is None:
        license_header = __GLOBAL_CONFIG__.cpp.license_header

    config = replace(
        __GLOBAL_CONFIG__.cpp,
        license_header=license_header,
    )

    dirs = get_dirs_in_dir() if dirs is None else [Path(d) for d in dirs]

    files = get_files_in_dirs(dirs)
    files = filter_cpp_files(files)

    rules = build_cpp_rules(config)
    run_cpp_checks(rules, config, dirs=dirs)
