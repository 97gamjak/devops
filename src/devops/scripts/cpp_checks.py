"""Module defining C++ check rules."""

from dataclasses import replace

import typer

from devops import __GLOBAL_CONFIG__
from devops.cpp import build_cpp_rules, run_cpp_checks

app = typer.Typer(help="C++ code quality checks.")


@app.command()
def cpp_checks(license_header: str | None = None) -> None:
    """Run C++ code quality checks.

    Parameters
    ----------
    license_header: str | None
        The license header text to check for. If None, uses the global configuration.

    """
    if license_header is None:
        license_header = __GLOBAL_CONFIG__.cpp.license_header

    config = replace(
        __GLOBAL_CONFIG__.cpp,
        license_header=license_header,
    )

    rules = build_cpp_rules(config)
    run_cpp_checks(rules, config)
