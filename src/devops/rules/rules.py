"""Module defining rules for mstd checks."""

from __future__ import annotations

import typing

from devops.enums import StrEnum
from devops.files import FileType

if typing.TYPE_CHECKING:
    from collections.abc import Callable

    from .result_type import ResultType


class RuleType(StrEnum):
    """Enumeration of rule types for mstd checks."""

    GENERAL = "GENERAL"
    CPP_STYLE = "CPP_STYLE"

    @classmethod
    def cpp_rules(cls) -> set[RuleType]:
        """Get a set of C++ related rule types.

        Returns
        -------
        set[RuleType]
            A set containing the C++ related rule types.

        """
        return {RuleType.CPP_STYLE}


class RuleInputType(StrEnum):
    """Enumeration of rule input types for mstd checks."""

    NONE = "NONE"
    LINE = "LINE"
    FILE = "FILE"


class Rule:
    """Base class for defining a rule."""

    cpp_style_rule_counter = 0
    general_rule_counter = 0

    @classmethod
    def increment_rule_counter(cls, rule_type: RuleType) -> tuple[str, int]:
        """Increment the rule counter based on the rule type.

        Parameters
        ----------
        rule_type: RuleType
            The type of the rule.

        Returns
        -------
        tuple[str, int]
            A string representing the rule type and the updated counter.

        Raises
        ------
        ValueError
            If the rule type is unknown.

        """
        if rule_type == RuleType.CPP_STYLE:
            return "STYLE", cls.increment_style_rule_counter()

        if rule_type == RuleType.GENERAL:
            return "GENERAL", cls.increment_general_rule_counter()

        msg = f"Unknown rule type: {rule_type}"
        raise ValueError(msg)

    @classmethod
    def increment_style_rule_counter(cls) -> int:
        """Increment the C++ style rule counter.

        Returns
        -------
        int
            The updated C++ style rule counter.

        """
        cls.cpp_style_rule_counter += 1
        return cls.cpp_style_rule_counter

    @classmethod
    def increment_general_rule_counter(cls) -> int:
        """Increment the general rule counter.

        Returns
        -------
        int
            The updated general rule counter.

        """
        cls.general_rule_counter += 1
        return cls.general_rule_counter

    def __init__(
        self,
        name: str,
        func: Callable,
        rule_type: RuleType = RuleType.GENERAL,
        rule_input_type: RuleInputType = RuleInputType.NONE,
        file_types: set[FileType] | None = None,
        description: str | None = None,
    ) -> None:
        """Initialize Rule with a name and optional description."""
        self.name = name
        self.description = description
        self.func = func
        self.rule_type = rule_type
        self.rule_input_type = rule_input_type

        if file_types is None and rule_type == RuleType.CPP_STYLE:
            # use only cpp file types if user gives explicit CPP_STYLE rule
            file_types = FileType.cpp_types()
        elif file_types is None:
            file_types = FileType.all_types()

        self.file_types = file_types

        self.rule_identifier = Rule.increment_rule_counter(rule_type)

    def apply(self, args: tuple) -> ResultType:
        """Apply the rule on a specific line.

        Parameters
        ----------
        args: tuple
            The arguments to pass to the rule function.

        Returns
        -------
        ResultType
            The result of applying the rule.

        """
        if isinstance(args, str):
            args = (args,)

        return self.func(*args) if args else self.func()


def filter_cpp_rules(rules: list[Rule]) -> list[Rule]:
    """Filter and return only C++ related rules.

    Parameters
    ----------
    rules: list[Rule]
        The list of rules to filter.

    Returns
    -------
    list[Rule]
        A list of C++ related rules.

    """
    return [rule for rule in rules if rule.rule_type in RuleType.cpp_rules()]


def filter_line_rules(rules: list[Rule]) -> list[Rule]:
    """Filter and return only line related rules.

    Parameters
    ----------
    rules: list[Rule]
        The list of rules to filter.

    Returns
    -------
    list[Rule]
        A list of line related rules.

    """
    return [rule for rule in rules if rule.rule_input_type == RuleInputType.LINE]


def filter_file_rules(rules: list[Rule]) -> list[Rule]:
    """Filter and return only file related rules.

    Parameters
    ----------
    rules: list[Rule]
        The list of rules to filter.

    Returns
    -------
    list[Rule]
        A list of file related rules.

    """
    return [rule for rule in rules if rule.rule_input_type == RuleInputType.FILE]


def is_line_rule(rule: Rule) -> bool:
    """Check if a rule is a line-based rule.

    Parameters
    ----------
    rule: Rule
        The rule to check.

    Returns
    -------
    bool
        True if the rule is line-based, False otherwise.

    """
    return rule.rule_input_type == RuleInputType.LINE


def is_file_rule(rule: Rule) -> bool:
    """Check if a rule is a file-based rule.

    Parameters
    ----------
    rule: Rule
        The rule to check.

    Returns
    -------
    bool
        True if the rule is file-based, False otherwise.

    """
    return rule.rule_input_type == RuleInputType.FILE
