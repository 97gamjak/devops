"""C++ rules for mstd devops."""

from __future__ import annotations

import re
import typing

from devops import __GLOBAL_CONFIG__
from devops.files import FileType
from devops.rules import ResultType, ResultTypeEnum, Rule, RuleInputType, RuleType
from devops.utils import check_key_sequence_ordered

if typing.TYPE_CHECKING:
    from pathlib import Path

    from devops.rules import FileRuleInput


class CheckKeySeqOrder(Rule):
    """Rule to check that a specific key sequence appears only in a given order."""

    def __init__(self, key_sequence: str) -> None:
        """Initialize CheckKeySeqOrder with the given key sequence.

        Parameters
        ----------
        key_sequence: str
            The key sequence to check.

        """
        super().__init__(
            name=key_sequence,
            func=lambda line: check_key_sequence_ordered(key_sequence, line),
            rule_type=RuleType.CPP_STYLE,
            rule_input_type=RuleInputType.LINE,
            description=f'Use "{key_sequence}" only in this given order.',
        )


class HeaderGuardError(Exception):
    """Custom exception for header guard errors."""


def find_define_macro(lines: list[str], macro: str) -> bool:
    """Check if the #define for the given macro exists in the lines.

    Parameters
    ----------
    lines: list[str]
        The lines of the header file.
    macro: str
        The header guard macro to look for.

    Returns
    -------
    bool
        True if the #define for the macro is found, False otherwise.

    """
    for _line in lines:
        line = _line.strip()
        if line.startswith("#define"):
            parts = line.split()
            if len(parts) <= 1:
                continue
            if parts[1] == macro:
                return True
    return False


def collect_header_guard_errors(lines: list[str]) -> tuple[str | None, list[str]]:
    """Find the header guard macro and collect all structural guard errors.

    Unlike raising on the first problem found, this gathers every applicable
    structural issue (missing ``#define``, a ``#define`` that doesn't
    immediately follow ``#ifndef``, a missing ``#endif``) so callers can
    report them all together instead of one at a time across repeated runs.

    Parameters
    ----------
    lines: list[str]
        The lines of the header file.

    Returns
    -------
    tuple[str | None, list[str]]
        The header guard macro if an ``#ifndef`` was found (else None), and
        the list of error messages describing every structural problem
        found. An empty list means the header guard is well-formed.

    """
    macro = None
    ifndef_idx = None
    # Search for the header guard macro near the beginning of the file.
    # Limit the search to the first N lines to avoid picking up feature-detection
    # or other conditional macros that appear later in the file.
    max_header_guard_search_lines = 50
    for idx, _line in enumerate(lines):
        if idx > max_header_guard_search_lines:
            break
        line = _line.strip()
        if line.startswith("#ifndef"):
            parts = line.split()
            if len(parts) <= 1:
                continue
            macro = parts[1]
            ifndef_idx = idx
            # Assume the first valid #ifndef within the search window is the
            # header guard and stop searching to avoid later #ifndef directives.
            break

    if macro is None:
        return None, ["Header guard macro not found with #ifndef."]

    errors = []

    is_defined = find_define_macro(lines, macro)
    next_line = lines[ifndef_idx + 1].strip() if ifndef_idx + 1 < len(lines) else ""
    if next_line != f"#define {macro}":
        if is_defined:
            errors.append(
                "Header guard '#define' must immediately follow '#ifndef' with "
                "no blank line or other content in between."
            )
        else:
            errors.append("Header guard macro not defined with #define.")

    if not any(line.lstrip().startswith("#endif") for line in lines):
        errors.append("Header guard missing closing #endif.")

    return macro, errors


def find_header_guard(lines: list[str]) -> str:
    """Find the header guard macro in the given lines.

    Parameters
    ----------
    lines: list[str]
        The lines of the header file.

    Returns
    -------
    str
        The header guard macro if found.

    Raises
    ------
    HeaderGuardError
        If the header guard is not properly defined. If more than one
        structural problem is present, all of them are reported together
        in a single error message.

    """
    macro, errors = collect_header_guard_errors(lines)

    if errors:
        raise HeaderGuardError(" ".join(errors))

    return typing.cast("str", macro)


_DEFAULT_HEADER_GUARD_PATTERN = "__{path}_{ext}__"

_PATH_PREFIXES_TO_STRIP = ("include/", "test/", "src/")

_KNOWN_EXTENSIONS = (
    (".impl.hpp", "IMPL_HPP"),
    (".hpp", "HPP"),
    (".tpp", "TPP"),
    (".h", "H"),
)

_CAMEL_WORD_BOUNDARY_1 = re.compile(r"(.)([A-Z][a-z]+)")
_CAMEL_WORD_BOUNDARY_2 = re.compile(r"([a-z0-9])([A-Z])")


def _camel_to_snake(name: str) -> str:
    """Convert a camelCase/PascalCase path segment to upper SNAKE_CASE.

    Word boundaries (lower-to-upper transitions) get an underscore inserted
    so e.g. ``velocityVerlet`` becomes ``VELOCITY_VERLET`` instead of being
    flattened to ``VELOCITYVERLET`` by a plain ``.upper()``. Segments that
    already use snake_case or are a single word are left as-is other than
    the case change.

    Parameters
    ----------
    name: str
        The path segment (directory name or file stem) to convert.

    Returns
    -------
    str
        The upper SNAKE_CASE form of the segment.

    """
    snake = _CAMEL_WORD_BOUNDARY_1.sub(r"\1_\2", name)
    snake = _CAMEL_WORD_BOUNDARY_2.sub(r"\1_\2", snake)
    return snake.upper()


def expected_header_guard_macro(path: Path, pattern: str | None) -> str:
    """Compute the expected header guard macro name for a file path.

    Parameters
    ----------
    path: Path
        The file path to derive the macro name from.
    pattern: str or None
        A format string with ``{path}`` and ``{ext}`` placeholders used to
        build the macro name, or None to use the default
        ``__{path}_{ext}__`` pattern. ``{path}`` is built from the path
        with any leading ``include/``, ``test/`` or ``src/`` directory
        removed and its extension stripped: each remaining directory and
        the file stem is converted from camelCase/PascalCase to
        SNAKE_CASE (so ``velocityVerlet`` becomes ``VELOCITY_VERLET``, not
        ``VELOCITYVERLET``), then joined with ``__``. ``{ext}`` is the
        upper-cased extension (``HPP``, ``IMPL_HPP``, ``TPP`` or ``H``).

    Returns
    -------
    str
        The expected header guard macro name.

    """
    raw_path = str(path).replace("\\", "/")
    lowered = raw_path.lower()
    for prefix in _PATH_PREFIXES_TO_STRIP:
        if lowered.startswith(prefix):
            raw_path = raw_path[len(prefix) :]
            break

    *dir_parts, filename = raw_path.split("/")

    ext = None
    stem = filename
    lowered_filename = filename.lower()
    for suffix, suffix_ext in _KNOWN_EXTENSIONS:
        if lowered_filename.endswith(suffix):
            stem = filename[: -len(suffix)]
            ext = suffix_ext
            break

    if ext is None:
        return "__".join(_camel_to_snake(part) for part in [*dir_parts, filename])

    macro_path = "__".join(_camel_to_snake(part) for part in [*dir_parts, stem])

    pattern = pattern or _DEFAULT_HEADER_GUARD_PATTERN
    return pattern.format(path=macro_path, ext=ext)


def check_header_guards(file_rule_input: FileRuleInput) -> ResultType:
    """Check if the C++ header file has proper header guards.

    Parameters
    ----------
    file_rule_input: FileRuleInput
        The input containing the file content and path to check.

    Returns
    -------
    ResultType
        The result of the header guard check.
    """
    file_content = file_rule_input.file_content
    path = file_rule_input.path

    lines = file_content.splitlines()
    guard_macro, errors = collect_header_guard_errors(lines)

    if (
        guard_macro is not None
        and __GLOBAL_CONFIG__.cpp.header_guards_according_to_filepath
        and path is not None
    ):
        expected_macro = expected_header_guard_macro(
            path, __GLOBAL_CONFIG__.cpp.header_guard_pattern
        )

        if guard_macro != expected_macro:
            errors.append(
                f"Header guard macro '{guard_macro}' does not match expected "
                f"macro '{expected_macro}' according to file path."
            )

    if errors:
        return ResultType(ResultTypeEnum.Error, " ".join(errors))

    return ResultType(ResultTypeEnum.Ok)


class CheckHeaderGuards(Rule):
    """Rule to check for proper header guards in C++ header files."""

    def __init__(self) -> None:
        """Initialize CheckHeaderGuards rule."""
        super().__init__(
            name="CheckHeaderGuards",
            description="Ensure that all C++ header files have proper header guards.",
            rule_type=RuleType.CPP_STYLE,
            rule_input_type=RuleInputType.FILE,
            file_types=[FileType.CPPHeader],
            func=check_header_guards,
        )


rule01 = CheckKeySeqOrder("static inline constexpr")
rule02 = CheckHeaderGuards()

cpp_style_rules = [rule01, rule02]
