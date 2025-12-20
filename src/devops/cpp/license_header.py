"""Module to check for license headers in C++ files."""

from __future__ import annotations

from pathlib import Path

from devops.files import file_exist
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

    with required_header_file.open("r", encoding="utf-8") as f:
        required_header = f.read()

        if file_content.startswith(required_header):
            return ResultType(ResultTypeEnum.Ok)

        return ResultType(ResultTypeEnum.Error, "Missing or incorrect license header.")


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
