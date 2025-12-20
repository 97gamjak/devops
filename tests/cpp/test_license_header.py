"""Tests for license header checking functionality."""

from __future__ import annotations

import typing

from devops.cpp.license_header import CheckLicenseHeader, check_license_header
from devops.rules import FileRuleInput, ResultTypeEnum, RuleInputType, RuleType

if typing.TYPE_CHECKING:
    from pathlib import Path


class TestCheckLicenseHeader:
    """Tests for check_license_header function."""

    def test_check_license_header_present(self, tmp_path: Path) -> None:
        """Test check when license header is present.

        Parameters
        ----------
        tmp_path: Path
            Temporary path for creating test files.

        """
        # Create a license header file
        header_file = tmp_path / "header.txt"
        header_file.write_text("// Copyright 2024\n// All rights reserved\n")

        # Create file content that starts with the header
        file_content = "// Copyright 2024\n// All rights reserved\n\nint main() {}\n"

        result = check_license_header(
            FileRuleInput(file_content=file_content), header_file
        )
        assert result.value == ResultTypeEnum.Ok

    def test_check_license_header_missing(self, tmp_path: Path) -> None:
        """Test check when license header is missing.

        Parameters
        ----------
        tmp_path: Path
            Temporary path for creating test files.

        """
        # Create a license header file
        header_file = tmp_path / "header.txt"
        header_file.write_text("// Copyright 2024\n// All rights reserved\n")

        # Create file content without the header
        file_content = "int main() {}\n"

        result = check_license_header(
            FileRuleInput(file_content=file_content), header_file
        )
        assert result.value == ResultTypeEnum.Error
        assert result.description == "Missing or incorrect license header."

    def test_check_license_header_incorrect(self, tmp_path: Path) -> None:
        """Test check when license header is incorrect.

        Parameters
        ----------
        tmp_path: Path
            Temporary path for creating test files.

        """
        # Create a license header file
        header_file = tmp_path / "header.txt"
        header_file.write_text("// Copyright 2024\n// All rights reserved\n")

        # Create file content with different header
        file_content = "// Copyright 2023\n// Some rights reserved\n\nint main() {}\n"

        result = check_license_header(
            FileRuleInput(file_content=file_content), header_file
        )
        assert result.value == ResultTypeEnum.Error
        assert result.description == "Missing or incorrect license header."

    def test_check_license_header_partial_match(self, tmp_path: Path) -> None:
        """Test check when only part of the header matches.

        Parameters
        ----------
        tmp_path: Path
            Temporary path for creating test files.

        """
        # Create a license header file
        header_file = tmp_path / "header.txt"
        header_file.write_text("// Copyright 2024\n// All rights reserved\n")

        # Create file content with only part of the header
        file_content = "// Copyright 2024\n\nint main() {}\n"

        result = check_license_header(
            FileRuleInput(file_content=file_content), header_file
        )
        assert result.value == ResultTypeEnum.Error

    def test_check_license_header_empty_file(self, tmp_path: Path) -> None:
        """Test check on empty file content.

        Parameters
        ----------
        tmp_path: Path
            Temporary path for creating test files.

        """
        # Create a license header file
        header_file = tmp_path / "header.txt"
        header_file.write_text("// Copyright 2024\n")

        # Empty file content
        file_content = ""

        result = check_license_header(
            FileRuleInput(file_content=file_content), header_file
        )
        assert result.value == ResultTypeEnum.Error

    def test_check_license_header_empty_header(self, tmp_path: Path) -> None:
        """Test check with empty license header.

        Parameters
        ----------
        tmp_path: Path
            Temporary path for creating test files.

        """
        # Create an empty license header file
        header_file = tmp_path / "header.txt"
        header_file.write_text("")

        # Any file content should pass with empty header
        file_content = "int main() {}\n"

        result = check_license_header(
            FileRuleInput(file_content=file_content), header_file
        )
        assert result.value == ResultTypeEnum.Ok

    def test_check_license_header_with_str_path(self, tmp_path: Path) -> None:
        """Test check using string path instead of Path object.

        Parameters
        ----------
        tmp_path: Path
            Temporary path for creating test files.

        """
        # Create a license header file
        header_file = tmp_path / "header.txt"
        header_file.write_text("// Header\n")

        # Create file content with the header
        file_content = "// Header\nint main() {}\n"

        result = check_license_header(
            FileRuleInput(file_content=file_content), str(header_file)
        )
        assert result.value == ResultTypeEnum.Ok

    def test_check_license_header_multiline(self, tmp_path: Path) -> None:
        """Test check with multiline license header.

        Parameters
        ----------
        tmp_path: Path
            Temporary path for creating test files.

        """
        # Create a multiline license header
        header_text = """/*
 * Copyright (c) 2024 Example Corp
 * All rights reserved.
 * This source code is licensed under the MIT license.
 */
"""
        header_file = tmp_path / "header.txt"
        header_file.write_text(header_text)

        # Create file content with the header
        file_content = header_text + "\n#include <iostream>\n\nint main() {}\n"

        result = check_license_header(
            FileRuleInput(file_content=file_content), header_file
        )
        assert result.value == ResultTypeEnum.Ok

    def test_check_license_header_with_leading_whitespace(self, tmp_path: Path) -> None:
        """Test check with license header containing leading whitespace.

        Parameters
        ----------
        tmp_path: Path
            Temporary path for creating test files.

        """
        # Create a license header with specific whitespace
        header_text = "  // Copyright 2024\n  // All rights reserved\n"
        header_file = tmp_path / "header.txt"
        header_file.write_text(header_text)

        # File content must match exactly including whitespace
        file_content = (
            "  // Copyright 2024\n  // All rights reserved\n\nint main() {}\n"
        )

        result = check_license_header(
            FileRuleInput(file_content=file_content), header_file
        )
        assert result.value == ResultTypeEnum.Ok


class TestCheckLicenseHeaderClass:
    """Tests for CheckLicenseHeader rule class."""

    def test_check_license_header_class_creation(self, tmp_path: Path) -> None:
        """Test CheckLicenseHeader class instantiation.

        Parameters
        ----------
        tmp_path: Path
            Temporary path for creating test files.

        """
        header_file = tmp_path / "header.txt"
        header_file.write_text("// Header\n")

        rule = CheckLicenseHeader(str(header_file))

        assert rule.name == "License Header Check"
        assert rule.rule_type == RuleType.CPP_STYLE
        assert rule.rule_input_type == RuleInputType.FILE

        desc = "Ensure that the file contains the required license header."
        assert rule.description == desc

    def test_check_license_header_class_apply_with_valid_content(
        self, tmp_path: Path
    ) -> None:
        """Test applying CheckLicenseHeader rule with valid content.

        Parameters
        ----------
        tmp_path: Path
            Temporary path for creating test files.

        """
        header_file = tmp_path / "header.txt"
        header_file.write_text("// Header\n")

        rule = CheckLicenseHeader(str(header_file))
        file_content = "// Header\nint main() {}\n"

        result = rule.apply(FileRuleInput(file_content=file_content))
        assert result.value == ResultTypeEnum.Ok

    def test_check_license_header_class_apply_with_invalid_content(
        self, tmp_path: Path
    ) -> None:
        """Test applying CheckLicenseHeader rule with invalid content.

        Parameters
        ----------
        tmp_path: Path
            Temporary path for creating test files.

        """
        header_file = tmp_path / "header.txt"
        header_file.write_text("// Header\n")

        rule = CheckLicenseHeader(str(header_file))
        file_content = "int main() {}\n"

        result = rule.apply(FileRuleInput(file_content=file_content, path=header_file))
        assert result.value == ResultTypeEnum.Error
        assert result.description == "Missing or incorrect license header."

    def test_check_license_header_class_with_path_object(self, tmp_path: Path) -> None:
        """Test CheckLicenseHeader class with Path object.

        Parameters
        ----------
        tmp_path: Path
            Temporary path for creating test files.

        """
        header_file = tmp_path / "header.txt"
        header_file.write_text("// Header\n")

        rule = CheckLicenseHeader(header_file)
        file_content = "// Header\nint main() {}\n"

        result = rule.apply(FileRuleInput(file_content=file_content, path=header_file))
        assert result.value == ResultTypeEnum.Ok
