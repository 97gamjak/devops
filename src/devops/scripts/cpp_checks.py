"""Module defining C++ check rules."""

import sys
from dataclasses import replace
from pathlib import Path

import typer

from devops import __GLOBAL_CONFIG__
from devops.cpp import build_cpp_rules, run_cpp_checks
from devops.cpp.state import DEFAULT_STATE_FILE
from devops.utils import mstd_print

app = typer.Typer(help="C++ code quality checks.")


@app.command()
def cpp_checks(
    license_header: str | None = None,
    dirs: list[str] | None = None,
    incremental: bool = typer.Option(
        False,
        "--incremental",
        help=(
            "Only re-check files that failed, are new, or were modified since "
            "the last run.  Results are stored in the state file so subsequent "
            "runs can skip already-passing files.  Can also be enabled via "
            "``incremental_state_file`` in the [cpp] TOML section."
        ),
    ),
    state_file: str | None = typer.Option(
        None,
        "--state-file",
        help=(
            "Path to the JSON file used to persist incremental check state. "
            "Implies --incremental when given.  Precedence (highest first): "
            "this option, ``incremental_state_file`` in [cpp] TOML, "
            f"default path (``{DEFAULT_STATE_FILE}``)."
        ),
    ),
) -> None:
    """Run C++ code quality checks.

    Parameters
    ----------
    license_header: str | None
        The path to the license header file. If None, uses the global configuration.
    dirs: list[str] | None
        List of directories to check.
        If None, uses all directories in the current directory.
    incremental: bool
        When True, only re-check files that are new, previously failed, or
        modified since the last run.  Can also be enabled via
        ``incremental_state_file`` in the [cpp] TOML section.
    state_file: str | None
        Explicit path to the JSON state file.  Implies incremental mode.
        When omitted, falls back to the TOML setting or the default path.

    """
    if license_header is None:
        license_header = __GLOBAL_CONFIG__.cpp.license_header

    config = replace(
        __GLOBAL_CONFIG__.cpp,
        license_header=license_header,
    )

    cli_dirs = [Path(d) for d in dirs] if dirs is not None else None

    # Resolve incremental state file path.
    # Priority: --state-file CLI > incremental_state_file TOML > DEFAULT_STATE_FILE.
    # Incremental mode is active when --incremental, --state-file, or TOML setting is used.
    if state_file is not None:
        state_path: Path | None = Path(state_file)
    elif incremental or config.incremental_state_file:
        state_path = (
            Path(config.incremental_state_file)
            if config.incremental_state_file
            else DEFAULT_STATE_FILE
        )
    else:
        state_path = None

    rules = build_cpp_rules(config)
    passed = run_cpp_checks(rules, config, dirs=cli_dirs, state_file=state_path)

    if not passed:
        mstd_print("C++ checks failed.")
        sys.exit(1)
