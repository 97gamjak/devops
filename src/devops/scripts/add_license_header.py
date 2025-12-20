"""Script to add license headers to C++ files."""

from pathlib import Path

import typer

from devops.cpp import add_license_header as add_license_header_func
from devops.files import filter_cpp_files, get_dirs_in_dir, get_files_in_dirs
from devops.utils import mstd_print

add_single_header = typer.Typer()
add_multiple_headers = typer.Typer()


@add_single_header.command()
def add_license_header(
    file_path: str, license_header_path: str, *, dry_run: bool = False
) -> None:
    """Add a license header to a specified file.

    Parameters
    ----------
    file_path: str
        The path to the file where the license header should be added.
    license_header_path: str
        The path to the license header file.
    dry_run: bool
        If True, only print the file that would be modified without making changes.

    """
    added = add_license_header_func(file_path, license_header_path, dry_run=dry_run)
    if added:
        mstd_print(f"✅ License header added to {file_path}")


@add_multiple_headers.command()
def add_license_header_to_files(
    license_header_path: str, dirs: list[str] | None = None, *, dry_run: bool = False
) -> None:
    """Add a license header to all valid files in a specified directory.

    Parameters
    ----------
    license_header_path: str
        The path to the license header file.
    dirs: list[str] | None
        List of directory paths to search for files.
        If None, uses the current directory.
    dry_run: bool
        If True, only print the files that would be modified without making changes.
    """
    dirs = get_dirs_in_dir() if dirs is None else [Path(d) for d in dirs]

    files = get_files_in_dirs(dirs)
    files = filter_cpp_files(files)

    for file in files:
        add_license_header(file, license_header_path, dry_run=dry_run)
