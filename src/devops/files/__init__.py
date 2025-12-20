"""Top level package for file operations in mstd checks."""

from pathlib import Path

from .files import (
    FileType,
    determine_file_type,
    file_exist,
    get_files_in_dirs,
    get_staged_files,
)

__EXECUTION_DIR__ = Path.cwd()

__all__ = [
    "__EXECUTION_DIR__",
    "FileType",
    "determine_file_type",
    "file_exist",
    "get_files_in_dirs",
    "get_staged_files",
]
