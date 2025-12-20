"""Module defining utility functions for mstd checks."""

from __future__ import annotations

import typing

from devops.config import Constants
from devops.logger import utils_logger
from devops.rules import ResultType, ResultTypeEnum

if typing.TYPE_CHECKING:
    from typing import Any


def find_indices(list_to_search: list[Any], element: Any) -> list[int]:
    """Find all indices of an element in a list.

    Parameters
    ----------
    list_to_search: list[Any]
        The list to search through.
    element: Any
        The element to find in the list.

    Returns
    -------
    list[int]
        A list of indices where the element is found.

    """
    return [index for index, value in enumerate(list_to_search) if value == element]


def check_key_sequence_ordered(
    key_sequence: str, line: str, key_delimiter: str = " "
) -> ResultType:
    """Check if keys in key_sequence appear in order on the given line.

    Parameters
    ----------
    key_sequence: str
        The sequence of keys to check for order as a string.
    line: str
        The line of text to check.
    key_delimiter: str
        The delimiter used to find the keys.

    Returns
    -------
    ResultType:
        Result of the check, Error if keys are out of order, Ok otherwise

    """
    key_sequence = key_sequence.split(key_delimiter)
    line_elements = line.split(key_delimiter)

    # If not all keys are present, return Ok
    if set(key_sequence).intersection(set(line_elements)) != set(key_sequence):
        return ResultType(ResultTypeEnum.Ok)

    indices = [find_indices(line_elements, key) for key in key_sequence]

    if len(indices) != len(key_sequence):
        msg = f"Expected {len(key_sequence)} indices, but got {len(indices)}. "
        msg += "This indicates an internal error. "
        msg += (
            f"Please report this issue at {Constants.github.github_devops_issues_url}."
        )
        raise ValueError(msg)

    found_indices = 0
    for index in indices[0]:
        found_indices = 1
        for i in range(1, len(indices)):
            if index + i in indices[i]:
                found_indices += 1
                continue
            break

    if found_indices == len(key_sequence):
        utils_logger.debug(
            "All keys from key_sequence %s are present "
            "in line %s and ordered correctly.",
            key_sequence,
            line,
        )
        return ResultType(ResultTypeEnum.Ok)

    return ResultType(
        ResultTypeEnum.Error,
        f"key_sequence {key_sequence} not ordered correctly in line {line}.",
    )
