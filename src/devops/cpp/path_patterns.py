"""Shared file-path pattern matching for per-check path exceptions/exclusions.

Used wherever a check's TOML config narrows its effect to (or excludes it
from) specific files or directories, e.g.
`devops.cpp.ast.checks.name_filtered.NameFilteredCheck`'s ``path_exceptions``
and `devops.cpp.ast.checks.enforce_cpp_only_include.EnforceCppOnlyInclude`'s
``exclude_paths``. Kept dependency-free (no libclang import) so it can also
be used by the plain-text `devops.cpp.cpp_only_include_scan` pre-check.
"""

from __future__ import annotations

import fnmatch


def matches_path(filename: str, pattern: str) -> bool:
    """Return True if *filename* matches *pattern*.

    *filename* is typically an absolute path (the AST engine resolves each
    checked file), while *pattern* is written relative to the project root
    (e.g. ``"src/units/"``), so matching is done against *filename*'s path
    components rather than requiring an exact prefix/whole-string match.

    Patterns ending with ``/`` are treated as directory prefixes: any file
    with that directory anywhere in its path is a match (covering all
    subdirectories). All other patterns are matched with
    :func:`fnmatch.fnmatch` against the trailing path components of the
    same depth as the pattern, so a pattern like ``"src/units/*.cpp"``
    matches regardless of what precedes ``src/`` in the absolute path.
    """
    norm = filename.replace("\\", "/")
    if pattern.endswith("/"):
        anchored = "/" + pattern.strip("/") + "/"
        return anchored in f"/{norm}" or norm.startswith(pattern)

    depth = pattern.count("/") + 1
    suffix = "/".join(norm.split("/")[-depth:])
    return fnmatch.fnmatch(norm, pattern) or fnmatch.fnmatch(suffix, pattern)
