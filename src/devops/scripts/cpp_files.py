"""Script to filter and print buggy C++ files in specified directories."""

from pathlib import Path

import typer

from devops.cpp import filter_buggy_cpp
from devops.files import filter_cpp_files, get_dirs_in_dir, get_files_in_dirs
from devops.utils import mstd_print

app = typer.Typer()


@app.command()
def filter_buggy_cpp_files(dirs: list[str] | None = None) -> None:
    """Filter and print buggy C++ files in specified directories.

    Parameters
    ----------
    dirs: list[str] | None
        List of directory paths to search for files.
        If None, uses the current directory.
    """
    dirs = get_dirs_in_dir() if dirs is None else [Path(d) for d in dirs]

    files = get_files_in_dirs(dirs)
    files = filter_cpp_files(files)

    non_buggy_files = filter_buggy_cpp(files)

    for file in non_buggy_files:
        mstd_print(file)
