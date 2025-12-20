"""Module to check for license headers in C++ files."""

from __future__ import annotations

from pathlib import Path

from devops.files import file_exist, open_file
from devops.rules import ResultType, ResultTypeEnum, Rule, RuleInputType, RuleType


def check_license_header(
    file_content: str, required_header_file: str | Path
) -> ResultType:
    """Check if the file content starts with the required license header.

    Parameters
    ----------
    file_content: str
        The content of the file to check.
    required_header_file: str | Path
        The path to the file containing the required license header.

    Returns
    -------
    ResultType
        The result of the license header check.

    Raises
    ------
    DevOpsFileNotFoundError
        If the required header file does not exist.
    """
    required_header_file = Path(required_header_file)

    # return value can be ignored as exception will be raised if file does not exist
    file_exist(
        required_header_file,
        throwing=True,
        throw_msg="Required license header file not found.",
    )

    with open_file(required_header_file, mode="r") as f:
        required_header = f.read()

        if file_content.startswith(required_header):
            return ResultType(ResultTypeEnum.Ok)

        return ResultType(ResultTypeEnum.Error, "Missing or incorrect license header.")


def add_license_header(
    file: str | Path, header_to_add: str | Path, *, dry_run: bool = False
) -> bool:
    """Add the license header to the file content if it's missing.

    Parameters
    ----------
    file: str | Path
        The path to the file to modify.
    header_to_add: str | Path
        The path to the file containing the license header to add.
    dry_run: bool
        If True, do not modify the file, only simulate the addition.

    Returns
    -------
    bool
        True if the license header was added, False if it was already present.

    Raises
    ------
    DevOpsFileNotFoundError
        If the header file does not exist.
    """
    header_to_add = Path(header_to_add)

    # return value can be ignored as exception will be raised if file does not exist
    file_exist(
        header_to_add,
        throwing=True,
        throw_msg="License header file to add not found.",
    )

    new_content = ""

    with open_file(file, mode="r") as f:
        file_content = f.read()

    with open_file(header_to_add, mode="r") as f:
        license_header = f.read()

        if not file_content.startswith(license_header):
            new_content = license_header + file_content

    if new_content and not dry_run:
        with open_file(file, mode="w") as f:
            f.write(new_content)

        return True

    return new_content and dry_run


class CheckLicenseHeader(Rule):
    """Rule to check for the presence of a license header in C++ files."""

    def __init__(self, header_to_check: str | Path) -> None:
        super().__init__(
            name="License Header Check",
            func=lambda content: check_license_header(content, header_to_check),
            rule_type=RuleType.CPP_STYLE,
            rule_input_type=RuleInputType.FILE,
            description="Ensure that the file contains the required license header.",
        )
