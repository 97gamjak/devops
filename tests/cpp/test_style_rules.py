"""Unit tests for C++ style rules."""

from devops.cpp.style_rules import CheckKeySeqOrder, cpp_style_rules, rule01
from devops.files import FileType
from devops.rules import ResultTypeEnum, Rule, RuleInputType, RuleType


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
