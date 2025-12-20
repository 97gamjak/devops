"""Module for file operations in mstd checks."""

from __future__ import annotations

import subprocess
import typing
from enum import Enum
from pathlib import Path

if typing.TYPE_CHECKING:
    from collections.abc import Iterable


class DevOpsFileNotFoundError(Exception):
    """Exception raised when a specified file is not found."""

    def __init__(self, filepath: Path, message: str | None = None) -> None:
        """Initialize the exception with the missing file path.

        Parameters
        ----------
        filepath: Path
            The path to the file that was not found.
        message: str | None
            Optional custom message for the exception.
        """
        self.filepath = filepath

        default_message = f"File not found: {filepath}"
        if message is not None:
            final_message = f"{default_message} - {message}"
        else:
            final_message = default_message

        super().__init__(final_message)


class FileType(Enum):
    """Enumeration of file types for mstd checks."""

    UNKNOWN = 0
    CPPHeader = 1
    CPPSource = 2
    CMakeLists = 3

    @classmethod
    def all_types(cls) -> set[FileType]:
        """Get a set of all defined file types.

        Returns
        -------
        set[FileType]:
            A set containing all file types.

        """
        return set(cls)

    @classmethod
    def cpp_types(cls) -> set[FileType]:
        """Get a set of all CPP related file types."""
        return {FileType.CPPHeader, FileType.CPPSource}

    @classmethod
    def is_cpp_type(cls, file_type: FileType) -> bool:
        """Check if the given file type is a C++ related type."""
        return file_type in cls.cpp_types()


def determine_file_type(filename: str | Path) -> FileType:
    """Determine the file type based on the filename extension.

    Parameters
    ----------
    filename: str | Path
        The name of the file to check.

    Returns
    -------
    FileType:
        The determined file type.

    """
    filename = str(filename)

    if filename.endswith((".h", ".hpp")):
        return FileType.CPPHeader
    if filename.endswith((".cpp", ".cxx", ".cc", ".c")):
        return FileType.CPPSource
    if filename == "CMakeLists.txt":
        return FileType.CMakeLists

    return FileType.UNKNOWN


def get_files_in_dirs(
    paths: Iterable[Path],
    exclude_dirs: list[str] | None = None,
    exclude_files: list[str] | None = None,
    max_recursion: int = 20,
) -> list[Path]:
    """Get all files in the specified directories.

    Parameters
    ----------
    paths: Iterable[Path]
        List of directory paths to search for files.
    exclude_dirs: list[str] | None
        List of directory names to exclude from the search. Defaults to None.
    exclude_files: list[str] | None
        List of file names to exclude from the search. Defaults to None.
    max_recursion: int
        Number of maximum recursion through dirs to avoid infinite recursion,
        default 20

    Returns
    -------
    list[Path]:
        List of file paths found in the specified directories.

    """
    if exclude_dirs is None:
        exclude_dirs = []

    if exclude_files is None:
        exclude_files = []

    all_files = []

    if max_recursion == 0:
        return all_files

    for path in paths:
        if path.is_dir() and path.name not in exclude_dirs:
            all_files.extend(
                get_files_in_dirs(
                    path.iterdir(), exclude_dirs, exclude_files, max_recursion - 1
                )
            )
        elif path.is_file() and path.name not in exclude_files:
            all_files.append(path)

    return all_files


def get_staged_files() -> list[Path]:
    """Get the list of staged files in the git repository.

    Returns
    -------
    list[Path]:
        List of staged file paths.

    Raises
    ------
    subprocess.CalledProcessError
        If the git command fails.

    """
    result = subprocess.run(
        ["git", "diff", "--name-only", "--cached"],
        capture_output=True,
        text=True,
        check=True,
    )

    files = result.stdout.strip().split("\n")
    return [Path(file) for file in files if file]


def file_exist(
    file: str | Path, *, throwing: bool = False, throw_msg: str | None = None
) -> bool:
    """Check if a file exists at the given path.

    Parameters
    ----------
    file: str | Path
        The path to the file to check.
    throwing: bool
        Whether to raise an exception if the file does not exist.
    throw_msg: str | None
        Custom message to use when raising an exception if the file does not exist.

    Returns
    -------
    bool
        True if the file exists, False otherwise.

    Raises
    ------
    DevOpsFileNotFoundError
        If the file does not exist and throwing is True.

    """
    filepath = Path(file)
    if filepath.is_file():
        return True

    if throwing:
        raise DevOpsFileNotFoundError(filepath, message=throw_msg)

    return False
