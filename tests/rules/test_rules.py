"""Unit tests for Rule class and related functionality."""

from devops.files import FileType
from devops.rules import (
    ResultType,
    ResultTypeEnum,
    Rule,
    RuleInputType,
    RuleType,
    filter_cpp_rules,
    filter_line_rules,
)


class TestRuleType:
    """Tests for RuleType enumeration."""

    def test_rule_type_values(self):
        """Test that RuleType has expected values."""
        assert RuleType.GENERAL.value == "GENERAL"
        assert RuleType.CPP_STYLE.value == "CPP_STYLE"

    def test_cpp_rules(self):
        """Test that cpp_rules returns correct set."""
        cpp_rules = RuleType.cpp_rules()
        assert isinstance(cpp_rules, set)
        assert RuleType.CPP_STYLE in cpp_rules
        assert RuleType.GENERAL not in cpp_rules


class TestRuleInputType:
    """Tests for RuleInputType enumeration."""

    def test_rule_input_type_values(self):
        """Test that RuleInputType has expected values."""
        assert RuleInputType.NONE.value == "NONE"
        assert RuleInputType.LINE.value == "LINE"
        assert RuleInputType.FILE.value == "FILE"


class TestRuleCreation:
    """Tests for Rule class creation."""

    def setup_method(self):
        """Reset rule counters before each test."""
        Rule.cpp_style_rule_counter = 0
        Rule.general_rule_counter = 0

    def test_rule_creation_with_defaults(self):
        """Test Rule creation with default parameters."""
        rule = Rule(
            name="test_rule",
            func=lambda x: ResultType(ResultTypeEnum.Ok),
        )
        assert rule.name == "test_rule"
        assert rule.rule_type == RuleType.GENERAL
        assert rule.rule_input_type == RuleInputType.NONE
        assert rule.file_types == FileType.all_types()
        assert rule.description is None

    def test_rule_creation_cpp_style(self):
        """Test Rule creation with CPP_STYLE type."""
        rule = Rule(
            name="cpp_style_rule",
            func=lambda x: ResultType(ResultTypeEnum.Ok),
            rule_type=RuleType.CPP_STYLE,
        )
        assert rule.rule_type == RuleType.CPP_STYLE
        assert rule.file_types == FileType.cpp_types()

    def test_rule_creation_with_custom_file_types(self):
        """Test Rule creation with custom file types."""
        custom_types = {FileType.CPPHeader}
        rule = Rule(
            name="custom_rule",
            func=lambda x: ResultType(ResultTypeEnum.Ok),
            file_types=custom_types,
        )
        assert rule.file_types == custom_types

    def test_rule_creation_with_description(self):
        """Test Rule creation with description."""
        rule = Rule(
            name="described_rule",
            func=lambda x: ResultType(ResultTypeEnum.Ok),
            description="Test description",
        )
        assert rule.description == "Test description"

    def test_rule_creation_line_input_type(self):
        """Test Rule creation with LINE input type."""
        rule = Rule(
            name="line_rule",
            func=lambda x: ResultType(ResultTypeEnum.Ok),
            rule_input_type=RuleInputType.LINE,
        )
        assert rule.rule_input_type == RuleInputType.LINE


class TestRuleCounters:
    """Tests for Rule counter functionality."""

    def setup_method(self):
        """Reset rule counters before each test."""
        Rule.cpp_style_rule_counter = 0
        Rule.general_rule_counter = 0

    def test_general_rule_counter_increment(self):
        """Test that general rule counter increments correctly."""
        initial_counter = Rule.general_rule_counter
        rule = Rule(
            name="general_rule",
            func=lambda x: ResultType(ResultTypeEnum.Ok),
            rule_type=RuleType.GENERAL,
        )
        assert rule.rule_identifier == ("GENERAL", initial_counter + 1)
        assert Rule.general_rule_counter == initial_counter + 1

    def test_cpp_style_rule_counter_increment(self):
        """Test that cpp style rule counter increments correctly."""
        initial_counter = Rule.cpp_style_rule_counter
        rule = Rule(
            name="cpp_style_rule",
            func=lambda x: ResultType(ResultTypeEnum.Ok),
            rule_type=RuleType.CPP_STYLE,
        )
        assert rule.rule_identifier == ("STYLE", initial_counter + 1)
        assert Rule.cpp_style_rule_counter == initial_counter + 1

    def test_multiple_rules_increment_counters(self):
        """Test that multiple rules increment counters correctly."""
        Rule(
            name="rule1",
            func=lambda x: ResultType(ResultTypeEnum.Ok),
            rule_type=RuleType.GENERAL,
        )
        Rule(
            name="rule2",
            func=lambda x: ResultType(ResultTypeEnum.Ok),
            rule_type=RuleType.GENERAL,
        )
        assert Rule.general_rule_counter == 2

        Rule(
            name="rule3",
            func=lambda x: ResultType(ResultTypeEnum.Ok),
            rule_type=RuleType.CPP_STYLE,
        )
        assert Rule.cpp_style_rule_counter == 1


class TestRuleApplication:
    """Tests for Rule apply method."""

    def setup_method(self):
        """Reset rule counters before each test."""
        Rule.cpp_style_rule_counter = 0
        Rule.general_rule_counter = 0

    def test_apply_with_string_arg(self):
        """Test Rule apply with string argument."""
        def check_func(line):
            if "hello" in line:
                return ResultType(ResultTypeEnum.Ok)
            return ResultType(ResultTypeEnum.Error, "No hello found")

        rule = Rule(name="hello_check", func=check_func)
        result = rule.apply("hello world")
        assert result.value == ResultTypeEnum.Ok

        result = rule.apply("goodbye world")
        assert result.value == ResultTypeEnum.Error

    def test_apply_with_tuple_arg(self):
        """Test Rule apply with tuple argument."""
        def check_func(a, b):
            if a == b:
                return ResultType(ResultTypeEnum.Ok)
            return ResultType(ResultTypeEnum.Error, "Values don't match")

        rule = Rule(name="match_check", func=check_func)
        result = rule.apply(("test", "test"))
        assert result.value == ResultTypeEnum.Ok

        result = rule.apply(("test1", "test2"))
        assert result.value == ResultTypeEnum.Error


class TestRuleFiltering:
    """Tests for rule filtering functions."""

    def setup_method(self):
        """Reset rule counters before each test."""
        Rule.cpp_style_rule_counter = 0
        Rule.general_rule_counter = 0

    def test_filter_cpp_rules(self):
        """Test filter_cpp_rules returns only C++ related rules."""
        cpp_rule = Rule(
            name="cpp_rule",
            func=lambda x: ResultType(ResultTypeEnum.Ok),
            rule_type=RuleType.CPP_STYLE,
        )
        general_rule = Rule(
            name="general_rule",
            func=lambda x: ResultType(ResultTypeEnum.Ok),
            rule_type=RuleType.GENERAL,
        )
        rules = [cpp_rule, general_rule]

        filtered = filter_cpp_rules(rules)
        assert len(filtered) == 1
        assert cpp_rule in filtered
        assert general_rule not in filtered

    def test_filter_cpp_rules_empty_list(self):
        """Test filter_cpp_rules with empty list."""
        filtered = filter_cpp_rules([])
        assert filtered == []

    def test_filter_cpp_rules_no_matches(self):
        """Test filter_cpp_rules when no rules match."""
        general_rule = Rule(
            name="general_rule",
            func=lambda x: ResultType(ResultTypeEnum.Ok),
            rule_type=RuleType.GENERAL,
        )
        filtered = filter_cpp_rules([general_rule])
        assert filtered == []

    def test_filter_line_rules(self):
        """Test filter_line_rules returns only line input rules."""
        line_rule = Rule(
            name="line_rule",
            func=lambda x: ResultType(ResultTypeEnum.Ok),
            rule_input_type=RuleInputType.LINE,
        )
        file_rule = Rule(
            name="file_rule",
            func=lambda x: ResultType(ResultTypeEnum.Ok),
            rule_input_type=RuleInputType.FILE,
        )
        none_rule = Rule(
            name="none_rule",
            func=lambda x: ResultType(ResultTypeEnum.Ok),
            rule_input_type=RuleInputType.NONE,
        )
        rules = [line_rule, file_rule, none_rule]

        filtered = filter_line_rules(rules)
        assert len(filtered) == 1
        assert line_rule in filtered
        assert file_rule not in filtered
        assert none_rule not in filtered

    def test_filter_line_rules_empty_list(self):
        """Test filter_line_rules with empty list."""
        filtered = filter_line_rules([])
        assert filtered == []
