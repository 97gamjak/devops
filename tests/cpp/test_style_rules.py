"""Unit tests for C++ style rules."""

from __future__ import annotations

import typing
from pathlib import Path
from unittest.mock import Mock, patch

from devops.cpp.style_rules import (
    CheckHeaderGuards,
    CheckKeySeqOrder,
    HeaderGuardError,
    check_header_guards,
    cpp_style_rules,
    find_define_macro,
    find_header_guard,
    rule01,
    rule02,
)
from devops.files import FileType
from devops.rules import FileRuleInput, ResultTypeEnum, Rule, RuleInputType, RuleType

if typing.TYPE_CHECKING:
    from pathlib import Path as PathType


class TestCheckKeySeqOrder:
    """Tests for CheckKeySeqOrder rule."""

    def setup_method(self) -> None:
        """Reset rule counters before each test."""
        Rule.cpp_style_rule_counter = 0
        Rule.general_rule_counter = 0

    def test_check_key_seq_order_creation(self) -> None:
        """Test CheckKeySeqOrder rule creation."""
        rule = CheckKeySeqOrder("static inline constexpr")
        assert rule.name == "static inline constexpr"
        assert rule.rule_type == RuleType.CPP_STYLE
        assert rule.rule_input_type == RuleInputType.LINE
        assert rule.description == (
            'Use "static inline constexpr" only in this given order.'
        )
        assert rule.file_types == FileType.cpp_types()

    def test_check_key_seq_order_correct_order(self) -> None:
        """Test CheckKeySeqOrder returns Ok for correct order."""
        rule = CheckKeySeqOrder("static inline constexpr")
        line = "static inline constexpr int x = 42;"
        result = rule.apply(line)
        assert result.value == ResultTypeEnum.Ok

    def test_check_key_seq_order_incorrect_order(self) -> None:
        """Test CheckKeySeqOrder returns Error for incorrect order."""
        rule = CheckKeySeqOrder("static inline constexpr")
        line = "inline static constexpr int x = 42;"
        result = rule.apply(line)
        assert result.value == ResultTypeEnum.Error

    def test_check_key_seq_order_missing_keys(self) -> None:
        """Test CheckKeySeqOrder returns Ok when keys are missing."""
        rule = CheckKeySeqOrder("static inline constexpr")
        line = "int x = 42;"
        result = rule.apply(line)
        assert result.value == ResultTypeEnum.Ok

    def test_check_key_seq_order_partial_keys(self) -> None:
        """Test CheckKeySeqOrder returns Ok when only some keys are present."""
        rule = CheckKeySeqOrder("static inline constexpr")
        line = "static int x = 42;"
        result = rule.apply(line)
        assert result.value == ResultTypeEnum.Ok

    def test_check_key_seq_order_different_sequence(self) -> None:
        """Test CheckKeySeqOrder with different key sequence."""
        rule = CheckKeySeqOrder("const int")
        line = "const int x = 42;"
        result = rule.apply(line)
        assert result.value == ResultTypeEnum.Ok

        line = "int const x = 42;"
        result = rule.apply(line)
        assert result.value == ResultTypeEnum.Error

    def test_rule_initialization(self) -> None:
        """Test that CheckKeySeqOrder is initialized correctly."""
        rule = CheckKeySeqOrder("static inline constexpr")

        assert rule.name == "static inline constexpr"
        assert rule.rule_type == RuleType.CPP_STYLE
        assert rule.rule_input_type == RuleInputType.LINE
        assert rule.description == (
            'Use "static inline constexpr" only in this given order.'
        )

    def test_rule_initialization_custom_key_sequence(self) -> None:
        """Test CheckKeySeqOrder with a different key sequence."""
        rule = CheckKeySeqOrder("const static")

        assert rule.name == "const static"
        assert rule.rule_type == RuleType.CPP_STYLE
        assert rule.rule_input_type == RuleInputType.LINE
        assert rule.description == 'Use "const static" only in this given order.'

    def test_apply_correct_order(self) -> None:
        """Test that rule passes when keys are in correct order."""
        rule = CheckKeySeqOrder("static inline constexpr")
        result = rule.apply("static inline constexpr int x = 42;")

        assert result.value == ResultTypeEnum.Ok

    def test_apply_incorrect_order(self) -> None:
        """Test that rule fails when keys are out of order."""
        rule = CheckKeySeqOrder("static inline constexpr")
        result = rule.apply("inline static constexpr int x = 42;")

        assert result.value == ResultTypeEnum.Error

    def test_apply_partial_keys_present(self) -> None:
        """Test that rule passes when only some keys are present."""
        rule = CheckKeySeqOrder("static inline constexpr")
        # Only "static" and "constexpr" are present, missing "inline"
        result = rule.apply("static constexpr int x = 42;")

        assert result.value == ResultTypeEnum.Ok

    def test_apply_no_keys_present(self) -> None:
        """Test that rule passes when no keys are present."""
        rule = CheckKeySeqOrder("static inline constexpr")
        result = rule.apply("int x = 42;")

        assert result.value == ResultTypeEnum.Ok

    def test_apply_single_key_present(self) -> None:
        """Test that rule passes when only a single key is present."""
        rule = CheckKeySeqOrder("static inline constexpr")
        result = rule.apply("static int x = 42;")

        assert result.value == ResultTypeEnum.Ok


class TestCppStyleRulesModule:
    """Tests for cpp_style_rules module."""

    def test_rule01_is_check_key_seq_order(self) -> None:
        """Test that rule01 is a CheckKeySeqOrder instance."""
        assert isinstance(rule01, CheckKeySeqOrder)

    def test_rule01_checks_static_inline_constexpr(self) -> None:
        """Test that rule01 checks for static inline constexpr ordering."""
        assert rule01.name == "static inline constexpr"

    def test_cpp_style_rules_list_not_empty(self) -> None:
        """Test that cpp_style_rules list is not empty."""
        assert len(cpp_style_rules) > 0

    def test_cpp_style_rules_contains_rule01(self) -> None:
        """Test that cpp_style_rules contains rule01."""
        assert rule01 in cpp_style_rules

    def test_all_cpp_style_rules_are_cpp_style_type(self) -> None:
        """Test that all rules in cpp_style_rules have CPP_STYLE type."""
        for rule in cpp_style_rules:
            assert rule.rule_type == RuleType.CPP_STYLE


class TestStaticInlineConstexprRule:
    """Tests for static inline constexpr ordering rule."""

    def setup_method(self) -> None:
        """Reset rule counters before each test."""
        Rule.cpp_style_rule_counter = 0
        Rule.general_rule_counter = 0

    def test_static_inline_constexpr_correct(self) -> None:
        """Test correct static inline constexpr order."""
        rule = CheckKeySeqOrder("static inline constexpr")
        test_cases = [
            "static inline constexpr int x = 42;",
            "    static inline constexpr auto value = 10;",
            "static inline constexpr double PI = 3.14159;",
        ]
        for line in test_cases:
            result = rule.apply(line)
            assert result.value == ResultTypeEnum.Ok, f"Failed for: {line}"

    def test_static_inline_constexpr_wrong_order(self) -> None:
        """Test wrong static inline constexpr order returns Error."""
        rule = CheckKeySeqOrder("static inline constexpr")
        test_cases = [
            "inline static constexpr int x = 42;",
            "constexpr static inline int x = 42;",
            "constexpr inline static int x = 42;",
            "inline constexpr static int x = 42;",
        ]
        for line in test_cases:
            result = rule.apply(line)
            assert result.value == ResultTypeEnum.Error, f"Expected Error for: {line}"

    def test_static_inline_constexpr_partial_present(self) -> None:
        """Test lines with only some keywords present."""
        rule = CheckKeySeqOrder("static inline constexpr")
        test_cases = [
            "static int x = 42;",
            "inline void func();",
            "constexpr int y = 10;",
            "static constexpr int z = 5;",
            "inline constexpr int w = 3;",
        ]
        for line in test_cases:
            result = rule.apply(line)
            assert result.value == ResultTypeEnum.Ok, f"Expected Ok for: {line}"

    def test_rule01_exists_and_configured(self) -> None:
        """Test that rule01 is properly configured."""
        assert rule01 is not None
        assert rule01.name == "static inline constexpr"
        assert rule01.rule_type == RuleType.CPP_STYLE
        assert rule01.rule_input_type == RuleInputType.LINE

    def test_rule01_in_cpp_style_rules(self) -> None:
        """Test that rule01 is in the cpp_style_rules list."""
        assert rule01 in cpp_style_rules
        assert len(cpp_style_rules) >= 1

    def test_static_inline_constexpr_correct_order(self) -> None:
        """Test static inline constexpr in correct order."""
        result = rule01.apply("static inline constexpr int value = 10;")
        assert result.value == ResultTypeEnum.Ok

    def test_static_inline_constexpr_wrong_order_inline_first(self) -> None:
        """Test inline static constexpr (wrong order)."""
        result = rule01.apply("inline static constexpr int value = 10;")
        assert result.value == ResultTypeEnum.Error

    def test_static_inline_constexpr_wrong_order_constexpr_first(self) -> None:
        """Test constexpr static inline (wrong order)."""
        result = rule01.apply("constexpr static inline int value = 10;")
        assert result.value == ResultTypeEnum.Error

    def test_static_inline_constexpr_wrong_order_constexpr_inline_static(self) -> None:
        """Test constexpr inline static (wrong order)."""
        result = rule01.apply("constexpr inline static int value = 10;")
        assert result.value == ResultTypeEnum.Error

    def test_static_constexpr_only(self) -> None:
        """Test static constexpr without inline (should pass - not all keys present)."""
        result = rule01.apply("static constexpr int value = 10;")
        assert result.value == ResultTypeEnum.Ok

    def test_inline_constexpr_only(self) -> None:
        """Test inline constexpr without static (should pass - not all keys present)."""
        result = rule01.apply("inline constexpr int value = 10;")
        assert result.value == ResultTypeEnum.Ok

    def test_no_keywords(self) -> None:
        """Test line with no relevant keywords."""
        result = rule01.apply("int value = 10;")
        assert result.value == ResultTypeEnum.Ok

    def test_with_template(self) -> None:
        """Test static inline constexpr in a template context."""
        result = rule01.apply(
            "template<typename T> static inline constexpr T default_value{};"
        )
        assert result.value == ResultTypeEnum.Ok

    def test_in_function_declaration(self) -> None:
        """Test static inline constexpr in a function declaration."""
        result = rule01.apply(
            "static inline constexpr auto compute() -> int { return 42; }"
        )
        assert result.value == ResultTypeEnum.Ok

    def test_wrong_order_in_function(self) -> None:
        """Test wrong order in function declaration."""
        result = rule01.apply(
            "inline static constexpr auto compute() -> int { return 42; }"
        )
        assert result.value == ResultTypeEnum.Error


class TestFindDefineMacro:
    """Tests for find_define_macro function."""

    def test_find_define_macro_present(self) -> None:
        """Test finding a #define macro that exists."""
        lines = [
            "#ifndef MY_HEADER_HPP",
            "#define MY_HEADER_HPP",
            "",
            "// code here",
            "#endif",
        ]
        result = find_define_macro(lines, "MY_HEADER_HPP")
        assert result is True

    def test_find_define_macro_not_present(self) -> None:
        """Test when #define macro does not exist."""
        lines = [
            "#ifndef MY_HEADER_HPP",
            "#define OTHER_MACRO",
            "",
            "// code here",
            "#endif",
        ]
        result = find_define_macro(lines, "MY_HEADER_HPP")
        assert result is False

    def test_find_define_macro_with_whitespace(self) -> None:
        """Test finding #define with leading/trailing whitespace."""
        lines = [
            "  #ifndef MY_HEADER_HPP  ",
            "  #define MY_HEADER_HPP  ",
            "",
            "// code here",
            "#endif",
        ]
        result = find_define_macro(lines, "MY_HEADER_HPP")
        assert result is True

    def test_find_define_macro_multiple_defines(self) -> None:
        """Test finding specific macro among multiple #defines."""
        lines = [
            "#ifndef MY_HEADER_HPP",
            "#define FIRST_MACRO",
            "#define MY_HEADER_HPP",
            "#define LAST_MACRO",
            "#endif",
        ]
        result = find_define_macro(lines, "MY_HEADER_HPP")
        assert result is True

    def test_find_define_macro_malformed_define(self) -> None:
        """Test with malformed #define (no macro name)."""
        lines = [
            "#ifndef MY_HEADER_HPP",
            "#define",
            "#endif",
        ]
        result = find_define_macro(lines, "MY_HEADER_HPP")
        assert result is False

    def test_find_define_macro_empty_lines(self) -> None:
        """Test with empty list of lines."""
        lines: list[str] = []
        result = find_define_macro(lines, "MY_HEADER_HPP")
        assert result is False


class TestFindHeaderGuard:
    """Tests for find_header_guard function."""

    def test_find_header_guard_valid(self) -> None:
        """Test finding a valid header guard."""
        lines = [
            "#ifndef MY_HEADER_HPP",
            "#define MY_HEADER_HPP",
            "",
            "// code here",
            "#endif",
        ]
        result = find_header_guard(lines)
        assert result == "MY_HEADER_HPP"

    def test_find_header_guard_missing_ifndef(self) -> None:
        """Test when #ifndef is missing."""
        lines = [
            "#define MY_HEADER_HPP",
            "",
            "// code here",
            "#endif",
        ]
        try:
            find_header_guard(lines)
            assert False, "Should have raised HeaderGuardError"
        except HeaderGuardError as e:
            assert "Header guard macro not found with #ifndef" in str(e)

    def test_find_header_guard_missing_define(self) -> None:
        """Test when #define is missing."""
        lines = [
            "#ifndef MY_HEADER_HPP",
            "",
            "// code here",
            "#endif",
        ]
        try:
            find_header_guard(lines)
            assert False, "Should have raised HeaderGuardError"
        except HeaderGuardError as e:
            assert "Header guard macro not defined with #define" in str(e)

    def test_find_header_guard_missing_endif(self) -> None:
        """Test when #endif is missing."""
        lines = [
            "#ifndef MY_HEADER_HPP",
            "#define MY_HEADER_HPP",
            "",
            "// code here",
        ]
        try:
            find_header_guard(lines)
            assert False, "Should have raised HeaderGuardError"
        except HeaderGuardError as e:
            assert "Header guard missing closing #endif" in str(e)

    def test_find_header_guard_malformed_ifndef(self) -> None:
        """Test with malformed #ifndef (no macro name)."""
        lines = [
            "#ifndef",
            "#define MY_HEADER_HPP",
            "#endif",
        ]
        try:
            find_header_guard(lines)
            assert False, "Should have raised HeaderGuardError"
        except HeaderGuardError as e:
            assert "Header guard macro not found with #ifndef" in str(e)

    def test_find_header_guard_with_whitespace(self) -> None:
        """Test header guard with leading/trailing whitespace."""
        lines = [
            "  #ifndef MY_HEADER_HPP  ",
            "  #define MY_HEADER_HPP  ",
            "",
            "// code here",
            "  #endif  ",
        ]
        result = find_header_guard(lines)
        assert result == "MY_HEADER_HPP"

    def test_find_header_guard_first_valid_ifndef(self) -> None:
        """Test that it finds the first valid #ifndef within search window."""
        lines = [
            "// Some comment",
            "#ifndef MY_HEADER_HPP",
            "#define MY_HEADER_HPP",
            "",
            "#ifndef FEATURE_DETECTION",
            "#define FEATURE_DETECTION",
            "#endif",
            "",
            "#endif",
        ]
        result = find_header_guard(lines)
        assert result == "MY_HEADER_HPP"

    def test_find_header_guard_beyond_search_limit(self) -> None:
        """Test that #ifndef beyond search limit is not found."""
        # Create a file with #ifndef after 50 lines
        lines = ["// comment line"] * 51
        lines.append("#ifndef MY_HEADER_HPP")
        lines.append("#define MY_HEADER_HPP")
        lines.append("#endif")

        try:
            find_header_guard(lines)
            assert False, "Should have raised HeaderGuardError"
        except HeaderGuardError as e:
            assert "Header guard macro not found with #ifndef" in str(e)


class TestCheckHeaderGuards:
    """Tests for check_header_guards function."""

    def test_check_header_guards_valid(self) -> None:
        """Test with valid header guards."""
        file_content = """#ifndef MY_HEADER_HPP
#define MY_HEADER_HPP

class MyClass {
public:
    void myMethod();
};

#endif
"""
        result = check_header_guards(FileRuleInput(file_content=file_content))
        assert result.value == ResultTypeEnum.Ok

    def test_check_header_guards_missing_ifndef(self) -> None:
        """Test with missing #ifndef."""
        file_content = """#define MY_HEADER_HPP

class MyClass {
public:
    void myMethod();
};

#endif
"""
        result = check_header_guards(FileRuleInput(file_content=file_content))
        assert result.value == ResultTypeEnum.Error
        assert "Header guard macro not found with #ifndef" in result.description

    def test_check_header_guards_missing_define(self) -> None:
        """Test with missing #define."""
        file_content = """#ifndef MY_HEADER_HPP

class MyClass {
public:
    void myMethod();
};

#endif
"""
        result = check_header_guards(FileRuleInput(file_content=file_content))
        assert result.value == ResultTypeEnum.Error
        assert "Header guard macro not defined with #define" in result.description

    def test_check_header_guards_missing_endif(self) -> None:
        """Test with missing #endif."""
        file_content = """#ifndef MY_HEADER_HPP
#define MY_HEADER_HPP

class MyClass {
public:
    void myMethod();
};
"""
        result = check_header_guards(FileRuleInput(file_content=file_content))
        assert result.value == ResultTypeEnum.Error
        assert "Header guard missing closing #endif" in result.description

    def test_check_header_guards_with_path_match_disabled(self) -> None:
        """Test header guards when path matching is disabled."""
        file_content = """#ifndef ANY_NAME_WORKS
#define ANY_NAME_WORKS

class MyClass {};

#endif
"""
        with patch("devops.cpp.style_rules.__GLOBAL_CONFIG__") as mock_config:
            mock_config.cpp.header_guards_according_to_filepath = False
            result = check_header_guards(
                FileRuleInput(
                    file_content=file_content, path=Path("include/test/myfile.hpp")
                )
            )
            assert result.value == ResultTypeEnum.Ok

    def test_check_header_guards_with_path_match_enabled_correct(self) -> None:
        """Test header guards with path matching enabled and correct macro."""
        file_content = """#ifndef __MYFILE_HPP__
#define __MYFILE_HPP__

class MyClass {};

#endif
"""
        with patch("devops.cpp.style_rules.__GLOBAL_CONFIG__") as mock_config:
            mock_config.cpp.header_guards_according_to_filepath = True
            result = check_header_guards(
                FileRuleInput(
                    file_content=file_content, path=Path("include/myfile.hpp")
                )
            )
            assert result.value == ResultTypeEnum.Ok

    def test_check_header_guards_with_path_match_enabled_incorrect(self) -> None:
        """Test header guards with path matching enabled but incorrect macro."""
        file_content = """#ifndef WRONG_MACRO_NAME
#define WRONG_MACRO_NAME

class MyClass {};

#endif
"""
        with patch("devops.cpp.style_rules.__GLOBAL_CONFIG__") as mock_config:
            mock_config.cpp.header_guards_according_to_filepath = True
            result = check_header_guards(
                FileRuleInput(
                    file_content=file_content, path=Path("include/myfile.hpp")
                )
            )
            assert result.value == ResultTypeEnum.Error
            assert "does not match expected macro" in result.description
            assert "__MYFILE_HPP__" in result.description

    def test_check_header_guards_with_include_prefix(self) -> None:
        """Test header guards with INCLUDE/ prefix in path."""
        file_content = """#ifndef __UTILS__HELPER_HPP__
#define __UTILS__HELPER_HPP__

class Helper {};

#endif
"""
        with patch("devops.cpp.style_rules.__GLOBAL_CONFIG__") as mock_config:
            mock_config.cpp.header_guards_according_to_filepath = True
            result = check_header_guards(
                FileRuleInput(
                    file_content=file_content, path=Path("INCLUDE/utils/helper.hpp")
                )
            )
            assert result.value == ResultTypeEnum.Ok

    def test_check_header_guards_with_test_prefix(self) -> None:
        """Test header guards with TEST/ prefix in path."""
        file_content = """#ifndef __MOCKS__MOCK_CLASS_HPP__
#define __MOCKS__MOCK_CLASS_HPP__

class MockClass {};

#endif
"""
        with patch("devops.cpp.style_rules.__GLOBAL_CONFIG__") as mock_config:
            mock_config.cpp.header_guards_according_to_filepath = True
            result = check_header_guards(
                FileRuleInput(
                    file_content=file_content, path=Path("TEST/mocks/mock_class.hpp")
                )
            )
            assert result.value == ResultTypeEnum.Ok

    def test_check_header_guards_with_h_extension(self) -> None:
        """Test header guards with .h extension."""
        file_content = """#ifndef __MYHEADER_HPP__
#define __MYHEADER_HPP__

void myFunction();

#endif
"""
        with patch("devops.cpp.style_rules.__GLOBAL_CONFIG__") as mock_config:
            mock_config.cpp.header_guards_according_to_filepath = True
            result = check_header_guards(
                FileRuleInput(
                    file_content=file_content, path=Path("include/myheader.h")
                )
            )
            assert result.value == ResultTypeEnum.Ok

    def test_check_header_guards_no_path_provided(self) -> None:
        """Test header guards when no path is provided."""
        file_content = """#ifndef MY_HEADER_HPP
#define MY_HEADER_HPP

class MyClass {};

#endif
"""
        with patch("devops.cpp.style_rules.__GLOBAL_CONFIG__") as mock_config:
            mock_config.cpp.header_guards_according_to_filepath = True
            result = check_header_guards(FileRuleInput(file_content=file_content))
            assert result.value == ResultTypeEnum.Ok

    def test_check_header_guards_nested_path(self) -> None:
        """Test header guards with deeply nested path."""
        file_content = """#ifndef __A__B__C__D__FILE_HPP__
#define __A__B__C__D__FILE_HPP__

class File {};

#endif
"""
        with patch("devops.cpp.style_rules.__GLOBAL_CONFIG__") as mock_config:
            mock_config.cpp.header_guards_according_to_filepath = True
            result = check_header_guards(
                FileRuleInput(
                    file_content=file_content, path=Path("include/a/b/c/d/file.hpp")
                )
            )
            assert result.value == ResultTypeEnum.Ok


class TestCheckHeaderGuardsRule:
    """Tests for CheckHeaderGuards rule class."""

    def setup_method(self) -> None:
        """Reset rule counters before each test."""
        Rule.cpp_style_rule_counter = 0
        Rule.general_rule_counter = 0

    def test_rule_initialization(self) -> None:
        """Test CheckHeaderGuards rule initialization."""
        rule = CheckHeaderGuards()
        assert rule.name == "CheckHeaderGuards"
        assert rule.rule_type == RuleType.CPP_STYLE
        assert rule.rule_input_type == RuleInputType.FILE
        assert rule.description == (
            "Ensure that all C++ header files have proper header guards."
        )
        assert rule.file_types == [FileType.CPPHeader]

    def test_rule_apply_valid(self) -> None:
        """Test applying rule to valid header file."""
        rule = CheckHeaderGuards()
        file_content = """#ifndef MY_HEADER_HPP
#define MY_HEADER_HPP

class MyClass {};

#endif
"""
        result = rule.apply(FileRuleInput(file_content=file_content))
        assert result.value == ResultTypeEnum.Ok

    def test_rule_apply_invalid(self) -> None:
        """Test applying rule to invalid header file."""
        rule = CheckHeaderGuards()
        file_content = """class MyClass {};
"""
        result = rule.apply(FileRuleInput(file_content=file_content))
        assert result.value == ResultTypeEnum.Error

    def test_rule02_is_check_header_guards(self) -> None:
        """Test that rule02 is a CheckHeaderGuards instance."""
        assert isinstance(rule02, CheckHeaderGuards)

    def test_rule02_in_cpp_style_rules(self) -> None:
        """Test that rule02 is in the cpp_style_rules list."""
        assert rule02 in cpp_style_rules

    def test_cpp_style_rules_contains_header_guard_rule(self) -> None:
        """Test that cpp_style_rules contains CheckHeaderGuards rule."""
        header_guard_rules = [
            rule for rule in cpp_style_rules if isinstance(rule, CheckHeaderGuards)
        ]
        assert len(header_guard_rules) == 1
        assert header_guard_rules[0] == rule02
