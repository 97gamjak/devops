"""Module for filtering known buggy C++ header files."""

import re

from devops import __GLOBAL_CONFIG__
from devops.files import open_file


def filter_buggy_cpp(files: list[str]) -> list[str]:
    """Filter out known buggy C++ header files from a list of files.

    Parameters
    ----------
    files: list[str]
        The list of file paths to filter.

    Returns
    -------
    list[str]
        The filtered list of file paths excluding known buggy C++ headers.

    """
    buggy_macros = __GLOBAL_CONFIG__.exclude.buggy_cpp_macros

    filtered_files = []
    for file in files:
        with open_file(file, mode="r") as f:
            content = f.read()
            for buggy_macro in buggy_macros:
                regex = rf"\b{re.escape(buggy_macro)}\(\"[^)]*\"\)"
                matches = re.findall(regex, content)
                if matches:
                    break
            else:
                filtered_files.append(file)

    return filtered_files
