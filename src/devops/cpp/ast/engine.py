"""Shared single-pass AST-walk engine for libclang-based C++ checks."""

from __future__ import annotations

import typing
from pathlib import Path

import clang.cindex as clang

from devops.cpp.ast.base import Diagnostic
from devops.cpp.ast.registry import ALL_CHECKS

if typing.TYPE_CHECKING:
    from devops.cpp.ast.base import Check

_HEADER_SUFFIXES = {".h", ".hpp", ".hxx", ".hh"}


def run_ast_checks(
    path: Path,
    content: str,
    compile_args: list[str],
    checks: list[Check] | None = None,
) -> list[Diagnostic]:
    """Parse `path` once and run every given AST check over it.

    Parameters
    ----------
    path: Path
        Path of the file being checked (used for diagnostics and parsing).
    content: str
        The file's current content, passed to libclang as an unsaved file
        so checks see exactly what devops already read from disk (or
        staged), instead of re-reading it.
    compile_args: list[str]
        Compiler flags (e.g. ``-std=c++23``, include paths) passed to
        libclang when parsing.
    checks: list[Check] | None
        The checks to run. Defaults to `ALL_CHECKS` (every registered
        check) when omitted — pass a filtered subset (see
        `devops.cpp.ast.registry.select_checks`) to run only some of them.

    Returns
    -------
    list[Diagnostic]
        All diagnostics raised by any of `checks`, sorted by location.

    """
    checks = ALL_CHECKS if checks is None else checks

    # Use the display/diagnostic path as-is; resolve to absolute for libclang
    # so that unsaved-file lookup and AST node locations are consistent.
    filename = str(path)
    filename_abs = str(path.resolve())

    is_header = path.suffix.lower() in _HEADER_SUFFIXES

    parse_options = (
        clang.TranslationUnit.PARSE_DETAILED_PROCESSING_RECORD
        | clang.TranslationUnit.PARSE_SKIP_FUNCTION_BODIES
    )

    index = clang.Index.create()
    if is_header:
        # Parse a virtual .cpp wrapper that #includes the header so that
        # libclang gets a proper translation-unit context.  Parsing a header
        # directly often causes TranslationUnitLoadError because libclang
        # expects a complete translation unit as its entry point.
        # Use absolute paths so libclang's internal path resolution can match
        # our unsaved-file entries (it normalises to absolute before lookup).
        wrapper_name = str(Path.cwd() / "__devops_ast_header_check__.cpp")
        wrapper_content = f'#include "{filename_abs}"\n'
        unsaved = [(filename_abs, content), (wrapper_name, wrapper_content)]
        parse_name = wrapper_name
        filter_name = filename_abs
    else:
        unsaved = [(filename, content)]
        parse_name = filename
        filter_name = filename

    try:
        translation_unit = index.parse(
            parse_name,
            args=compile_args,
            unsaved_files=unsaved,
            options=parse_options,
        )
    except clang.TranslationUnitLoadError:
        return [
            Diagnostic(
                file=filename,
                line=0,
                column=0,
                message=(
                    "libclang could not parse this file — it may use GCC extensions "
                    "or built-ins that libclang does not support"
                ),
                check_id="astParseError",
                severity="error",
            )
        ]

    diagnostics: list[Diagnostic] = []

    for cursor in translation_unit.cursor.walk_preorder():
        loc = cursor.location
        if not loc.file or loc.file.name != filter_name:
            continue
        for check in checks:
            diagnostics.extend(check.visit(cursor, filename))

    for check in checks:
        diagnostics.extend(check.finalize(filename))

    return sorted(diagnostics, key=lambda d: (d.line, d.column))
