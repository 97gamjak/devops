"""Tests for the forbidden spellings rule."""

from __future__ import annotations

from pathlib import Path

import pytest

from devops.config.base import ConfigError
from devops.config.config_cpp import CppConfig, ForbiddenSpelling, parse_cpp_config
from devops.cpp.build_rules import build_cpp_rules
from devops.cpp.forbidden_spellings import CheckForbiddenSpellings
from devops.rules import FileRuleInput, ResultTypeEnum, RuleInputType, RuleType


class TestCheckForbiddenSpellings:
    """Tests for CheckForbiddenSpellings."""

    def setup_method(self) -> None:
        """Create the rule under test."""
        self.rule = CheckForbiddenSpellings(
            {
                "colour": ForbiddenSpelling("color"),
                "e.g": ForbiddenSpelling("for example"),
                "grey": ForbiddenSpelling("gray", within_words=True),
            }
        )

    def _apply(self, content: str) -> object:
        return self.rule.apply(FileRuleInput(content, Path("file.cpp")))

    def test_reports_file_and_line(self) -> None:
        """Each finding is reported as path:line."""
        result = self._apply("int ok;\n\n// colour\nint x; // colour e.g\n")
        assert "file.cpp:3:" in result.description
        assert "file.cpp:4:" in result.description
        assert "file.cpp:1:" not in result.description

    def test_rule_metadata(self) -> None:
        """The rule is a file-based C++ style rule."""
        assert self.rule.rule_type == RuleType.CPP_STYLE
        assert self.rule.rule_input_type == RuleInputType.FILE

    def test_ok_line(self) -> None:
        """A line without forbidden spellings passes."""
        assert self._apply("int color = 1;\n").value == ResultTypeEnum.Ok

    def test_flags_word_with_replacement(self) -> None:
        """A forbidden word is flagged and the replacement is named."""
        result = self._apply("// the colour of it\n")
        assert result.value == ResultTypeEnum.Error
        assert "'colour' -> 'color'" in result.description

    def test_whole_word_only(self) -> None:
        """Substrings of longer words are not flagged."""
        assert self._apply("int colourful = 1;\n").value == ResultTypeEnum.Ok
        assert self._apply("int mycolour = 1;\n").value == ResultTypeEnum.Ok

    def test_within_words(self) -> None:
        """A within_words spelling is also flagged inside longer words."""
        result = self._apply("int greyScale = 1;\n")
        assert result.value == ResultTypeEnum.Error
        assert "'grey' -> 'gray'" in result.description
        assert self._apply("int Grey = 1;\n").value == ResultTypeEnum.Ok

    def test_case_sensitive(self) -> None:
        """Matching is case-sensitive."""
        assert self._apply("Colour\n").value == ResultTypeEnum.Ok

    def test_special_characters_are_escaped(self) -> None:
        """Regex metacharacters in spellings are matched literally."""
        assert self._apply("// e.g and so on\n").value == ResultTypeEnum.Error
        assert self._apply("// eXg\n").value == ResultTypeEnum.Ok

    def test_multiple_findings_reported(self) -> None:
        """All distinct forbidden spellings in a line are reported."""
        result = self._apply("colour e.g colour\n")
        assert "'colour'" in result.description
        assert "'e.g'" in result.description


class TestForbiddenSpellingsConfig:
    """Tests for config parsing and rule building."""

    def test_default_is_empty(self) -> None:
        """No spellings are configured by default."""
        assert parse_cpp_config({}).forbidden_spellings == {}

    def test_parse(self) -> None:
        """The table is parsed into a dict."""
        raw = {"cpp": {"forbidden_spellings": {"colour": "color"}}}
        assert parse_cpp_config(raw).forbidden_spellings == {
            "colour": ForbiddenSpelling("color")
        }

    def test_parse_table_form(self) -> None:
        """The inline-table form sets within_words."""
        spelling = {"replacement": "color", "within_words": True}
        raw = {"cpp": {"forbidden_spellings": {"colour": spelling}}}
        assert parse_cpp_config(raw).forbidden_spellings["colour"] == (
            ForbiddenSpelling("color", within_words=True)
        )

    @pytest.mark.parametrize(
        "value",
        [
            {"within_words": True},
            {"replacement": "c", "within_words": "yes"},
            {"replacement": "c", "typo": 1},
        ],
    )
    def test_invalid_table_raises(self, value: dict) -> None:
        """Malformed inline tables are config errors."""
        with pytest.raises(ConfigError):
            parse_cpp_config({"cpp": {"forbidden_spellings": {"colour": value}}})

    def test_misplaced_cpp_option_hint(self) -> None:
        """A [cpp] option swallowed by the table gets an explanatory message."""
        raw = {"cpp": {"forbidden_spellings": {"ast_check_compile_args": ["-std"]}}}
        with pytest.raises(ConfigError, match="belongs to that table"):
            parse_cpp_config(raw)

    def test_non_string_replacement_raises(self) -> None:
        """A non-string replacement is a config error."""
        raw = {"cpp": {"forbidden_spellings": {"colour": 1}}}
        with pytest.raises(ConfigError):
            parse_cpp_config(raw)

    def test_empty_spelling_raises(self) -> None:
        """An empty spelling is a config error."""
        raw = {"cpp": {"forbidden_spellings": {"": "x"}}}
        with pytest.raises(ConfigError):
            parse_cpp_config(raw)

    def test_rule_built_only_when_configured(self) -> None:
        """The rule is added to the rule list only if spellings are set."""
        base = {"ast_checks": False, "license_header_check": False}
        none = build_cpp_rules(CppConfig(**base))
        some = build_cpp_rules(
            CppConfig(**base, forbidden_spellings={"a": ForbiddenSpelling("b")})
        )
        assert not any(isinstance(r, CheckForbiddenSpellings) for r in none)
        assert any(isinstance(r, CheckForbiddenSpellings) for r in some)
