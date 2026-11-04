"""Plain-text scanning for cpp-only header violations.

This mirrors the semantics of the `enforceCppOnlyInclude` AST check
(`devops.cpp.ast.checks.enforce_cpp_only_include`) but works purely off of
a file's raw text via regex, with no libclang parse involved. Two
consequences make that useful:

- It has no dependency on the optional ``ast`` extra, so it runs even when
  libclang isn't installed.
- It can be run as a standalone, whole-project pre-check (see
  `devops.cpp.checks.run_cpp_only_include_precheck`) over every header
  file, independent of whatever subset of files a given invocation is
  scoped to (a ``--base-ref`` diff, staged files, or an incremental-state
  skip) — a violation sitting in an untouched header can't silently pass
  just because that header wasn't part of the current run's selection.
"""

from __future__ import annotations

import fnmatch
import re
import typing

from devops.cpp.ast.base import Diagnostic

if typing.TYPE_CHECKING:
    from collections.abc import Iterable

#: Matches a preprocessor #include directive, capturing the included path
#: whether it's quoted or angle-bracketed.
_INCLUDE_RE = re.compile(r'^\s*#\s*include\s*[<"]([^">]+)[">]')

#: Shared with `devops.cpp.ast.checks.enforce_cpp_only_include`'s check id,
#: duplicated here (rather than imported) so this module never needs to
#: import that check module and, transitively, libclang.
CHECK_ID = "enforceCppOnlyInclude"


def find_includes(content: str) -> list[tuple[int, str]]:
    """Return every #include directive in `content` as (line number, path).

    Parameters
    ----------
    content: str
        The file's full text.

    Returns
    -------
    list[tuple[int, str]]
        One ``(1-based line number, include path)`` pair per ``#include``
        line found, in file order.

    """
    includes = []
    for lineno, line in enumerate(content.splitlines(), start=1):
        match = _INCLUDE_RE.match(line)
        if match:
            includes.append((lineno, match.group(1)))
    return includes


def matches_cpp_only_header(include_path: str, headers: Iterable[str]) -> bool:
    """Return whether `include_path` matches a configured cpp-only header pattern.

    Parameters
    ----------
    include_path: str
        The ``#include`` path exactly as written in the source.
    headers: Iterable[str]
        `fnmatch` patterns (matched against both the full path and its
        basename), as configured under
        ``[cpp.ast_check_config.enforceCppOnlyInclude].headers``.

    Returns
    -------
    bool
        True if `include_path` matches any pattern in `headers`.

    """
    basename = include_path.rsplit("/", 1)[-1]
    return any(
        fnmatch.fnmatch(include_path, pattern) or fnmatch.fnmatch(basename, pattern)
        for pattern in headers
    )


def scan_text_for_violations(
    filename: str, content: str, headers: Iterable[str]
) -> list[Diagnostic]:
    """Scan a header file's raw text for #includes of a configured cpp-only header.

    Parameters
    ----------
    filename: str
        Path of the header file being scanned (used for diagnostics only;
        the caller is responsible for only scanning actual header files).
    content: str
        The file's full text.
    headers: Iterable[str]
        The configured cpp-only header patterns (see
        `matches_cpp_only_header`).

    Returns
    -------
    list[Diagnostic]
        One diagnostic per ``#include`` line matching a configured
        cpp-only header pattern.

    """
    return [
        Diagnostic(
            file=filename,
            line=lineno,
            column=1,
            message=(
                f'#include "{include_path}" is only allowed from .cpp files, '
                "not from other header files"
            ),
            check_id=CHECK_ID,
            severity="error",
        )
        for lineno, include_path in find_includes(content)
        if matches_cpp_only_header(include_path, headers)
    ]
