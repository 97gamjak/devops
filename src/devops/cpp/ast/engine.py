"""Shared single-pass AST-walk engine for libclang-based C++ checks."""

from __future__ import annotations

import functools
import shutil
import subprocess
import typing
from pathlib import Path

import clang.cindex as clang

from devops.cpp.ast.base import Diagnostic
from devops.cpp.ast.registry import ALL_CHECKS

if typing.TYPE_CHECKING:
    from devops.cpp.ast.base import Check

_HEADER_SUFFIXES = {".h", ".hpp", ".hxx", ".hh", ".tpp"}


@functools.cache
def _resource_dir_for_compiler(compiler: str) -> str | None:
    """Ask `compiler` for its builtin resource-dir via ``-print-resource-dir``.

    Pip's ``libclang`` wheel ships only the shared library, not the builtin
    headers (``stddef.h`` and friends) a real Clang install carries under its
    resource directory. Without ``-resource-dir`` pointing at a real one,
    libclang hits a fatal error as soon as parsing reaches a standard header
    that needs them (e.g. via ``<locale>`` or ``<format>``), silently
    truncating the AST for the rest of the file. GCC compilers don't support
    this flag and simply return None here, leaving compile args unchanged.

    Parameters
    ----------
    compiler: str
        The compiler executable to query, e.g. ``"clang++"`` or a path from
        a compile_commands.json entry's argv[0].

    Returns
    -------
    str | None
        The resource directory path, or None if it could not be determined
        (unknown/non-Clang compiler, not found on PATH, etc.).

    """
    try:
        result = subprocess.run(  # noqa: S603 - no shell, compiler path is trusted
            [compiler, "-print-resource-dir"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        return None
    return result.stdout.strip() or None


def _has_resource_dir(args: list[str]) -> bool:
    """Check whether `args` already sets ``-resource-dir``."""
    return any(
        arg == "-resource-dir" or arg.startswith("-resource-dir=") for arg in args
    )


def _with_auto_resource_dir(args: list[str], compiler: str) -> list[str]:
    """Append an auto-detected ``-resource-dir`` for `compiler` if not already set.

    Parameters
    ----------
    args: list[str]
        The compile args to (possibly) extend.
    compiler: str
        The compiler executable to query via `_resource_dir_for_compiler`.

    Returns
    -------
    list[str]
        `args` unchanged if it already sets ``-resource-dir`` or none could
        be auto-detected; otherwise `args` plus ``-resource-dir=<path>``.

    """
    if _has_resource_dir(args):
        return args
    resource_dir = _resource_dir_for_compiler(compiler)
    if resource_dir is None:
        return args
    return [*args, f"-resource-dir={resource_dir}"]


def _with_fallback_resource_dir(args: list[str]) -> list[str]:
    """Add a best-effort ``-resource-dir`` using whatever Clang is on PATH.

    Callers that know the project's own compiler (e.g. from
    compile_commands.json) should resolve `_with_auto_resource_dir` against
    that compiler themselves first — it is more likely to match the code
    being parsed. This is the fallback for callers (including direct
    `run_ast_checks` callers) that don't have a specific compiler in hand.

    Parameters
    ----------
    args: list[str]
        The compile args to (possibly) extend.

    Returns
    -------
    list[str]
        `args` unchanged if it already sets ``-resource-dir`` or no Clang is
        on PATH; otherwise `args` plus ``-resource-dir=<path>``.

    """
    if _has_resource_dir(args):
        return args
    clang_exe = shutil.which("clang++") or shutil.which("clang")
    if clang_exe is None:
        return args
    return _with_auto_resource_dir(args, clang_exe)


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
    compile_args = _with_fallback_resource_dir(compile_args)

    # Use the display/diagnostic path as-is; resolve to absolute for libclang
    # so that unsaved-file lookup and AST node locations are consistent.
    filename = str(path)
    filename_abs = str(path.resolve())

    is_header = path.suffix.lower() in _HEADER_SUFFIXES

    # Function bodies are parsed in full (not PARSE_SKIP_FUNCTION_BODIES) so
    # checks that need statement-level cursors, such as noThrowParen, can see
    # inside them.
    parse_options = clang.TranslationUnit.PARSE_DETAILED_PROCESSING_RECORD

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

    # A fatal diagnostic (e.g. an unresolvable #include) aborts libclang's
    # parse partway through the file: everything after that point is absent
    # from the AST, so checks silently see less than the whole file with no
    # indication why. Surface it instead of letting that pass silently — the
    # checks below still run against whatever *was* parsed.
    fatal = next(
        (
            d
            for d in translation_unit.diagnostics
            if d.severity >= clang.Diagnostic.Fatal
        ),
        None,
    )
    if fatal is not None:
        diagnostics.append(
            Diagnostic(
                file=filename,
                line=fatal.location.line,
                column=fatal.location.column,
                message=(
                    "libclang hit a fatal error while parsing this file — "
                    "everything after this point was not parsed, so checks "
                    f"may have missed issues there: {fatal.spelling}"
                ),
                check_id="astParseError",
                severity="error",
            )
        )

    for cursor in translation_unit.cursor.walk_preorder():
        loc = cursor.location
        if not loc.file or loc.file.name != filter_name:
            continue
        for check in checks:
            diagnostics.extend(check.visit(cursor, filename))

    for check in checks:
        diagnostics.extend(check.finalize(filename))

    return sorted(diagnostics, key=lambda d: (d.line, d.column))
