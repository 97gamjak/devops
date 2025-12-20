"""C++ rules for mstd devops."""

from __future__ import annotations

import typing

from devops import __GLOBAL_CONFIG__
from devops.files import FileType
from devops.rules import ResultType, ResultTypeEnum, Rule, RuleInputType, RuleType
from devops.utils import check_key_sequence_ordered

if typing.TYPE_CHECKING:
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
        If the header guard is not properly defined.

    """
    macro = None
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
            # Assume the first valid #ifndef within the search window is the
            # header guard and stop searching to avoid later #ifndef directives.
            break

    if macro is None:
        msg = "Header guard macro not found with #ifndef."
        raise HeaderGuardError(msg)

    is_defined = find_define_macro(lines, macro)

    if not is_defined:
        msg = "Header guard macro not defined with #define."
        raise HeaderGuardError(msg)

    if not any(line.lstrip().startswith("#endif") for line in lines):
        msg = "Header guard missing closing #endif."
        raise HeaderGuardError(msg)

    return macro


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
    try:
        guard_macro = find_header_guard(lines)
    except HeaderGuardError as e:
        return ResultType(ResultTypeEnum.Error, str(e))

    if __GLOBAL_CONFIG__.cpp.header_guards_according_to_filepath and path is not None:
        expected_macro = str(path).upper()
        expected_macro = expected_macro.removeprefix("INCLUDE/")
        expected_macro = expected_macro.removeprefix("TEST/")
        expected_macro = expected_macro.replace("/", "__")
        expected_macro = expected_macro.removesuffix(".HPP")
        expected_macro = expected_macro.removesuffix(".H")
        expected_macro = "__" + expected_macro + "_HPP__"

        if guard_macro != expected_macro:
            msg = (
                f"Header guard macro '{guard_macro}' does not match expected "
                f"macro '{expected_macro}' according to file path."
            )
            return ResultType(ResultTypeEnum.Error, msg)

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
