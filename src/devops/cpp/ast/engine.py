"""Shared single-pass AST-walk engine for libclang-based C++ checks."""

from __future__ import annotations

import typing

import clang.cindex as clang

from devops.cpp.ast.registry import ALL_CHECKS
from devops.logger import cpp_check_logger

if typing.TYPE_CHECKING:
    from pathlib import Path

from devops.cpp.ast.base import Diagnostic

if typing.TYPE_CHECKING:
    from devops.cpp.ast.base import Check


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

    filename = str(path)
    _HEADER_SUFFIXES = {".h", ".hpp", ".hxx", ".hh"}
    is_header = path.suffix.lower() in _HEADER_SUFFIXES

    parse_options = (
        clang.TranslationUnit.PARSE_DETAILED_PROCESSING_RECORD
        | clang.TranslationUnit.PARSE_SKIP_FUNCTION_BODIES
    )
    if is_header:
        # CXTranslationUnit_Incomplete: tells libclang this is a header that
        # may not have all definitions present — prevents a catastrophic parse
        # failure (TranslationUnitLoadError) when scanning headers standalone.
        parse_options |= clang.TranslationUnit.PARSE_INCOMPLETE

    index = clang.Index.create()
    try:
        translation_unit = index.parse(
            filename,
            args=compile_args,
            unsaved_files=[(filename, content)],
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
        if not loc.file or loc.file.name != filename:
            continue
        for check in checks:
            diagnostics.extend(check.visit(cursor, filename))

    for check in checks:
        diagnostics.extend(check.finalize(filename))

    return sorted(diagnostics, key=lambda d: (d.line, d.column))
