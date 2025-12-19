"""Tests for devops.utils.check_key_sequence_ordered."""

from devops.rules import ResultTypeEnum
from devops.utils import check_key_sequence_ordered


def test_check_key_sequence_ordered() -> None:
    """Test the basic functionality of check_key_sequence_ordered."""
    keys = "static inline constexpr"
    line = "static inline constexpr int x = 42;"
    result = check_key_sequence_ordered(keys, line)
    assert result.value == ResultTypeEnum.Ok

    line = "inline static constexpr int x = 42;"
    result = check_key_sequence_ordered(keys, line)
    assert result.value == ResultTypeEnum.Error


def test_check_key_sequence_ordered_first_key_not_in_line() -> None:
    """Test when the first key doesn't appear in the line."""
    keys = "static inline constexpr"
    # Line doesn't contain 'static' (first key)
    line = "inline constexpr int x = 42;"
    result = check_key_sequence_ordered(keys, line)
    # Should return Ok since not all keys are present
    assert result.value == ResultTypeEnum.Ok


def test_check_key_sequence_ordered_no_keys_in_line() -> None:
    """Test when none of the keys appear in the line."""
    keys = "static inline constexpr"
    line = "int x = 42;"
    result = check_key_sequence_ordered(keys, line)
    assert result.value == ResultTypeEnum.Ok


def test_check_key_sequence_ordered_keys_multiple_positions() -> None:
    """Test when keys appear multiple times in different positions."""
    keys = "static inline"
    # 'static' appears twice, second occurrence is followed by 'inline'
    line = "static int static inline foo();"
    result = check_key_sequence_ordered(keys, line)
    # Should be Ok because the sequence 'static inline' exists in the line
    assert result.value == ResultTypeEnum.Ok


def test_check_key_sequence_ordered_keys_multiple_positions_wrong_order() -> None:
    """Test when keys appear multiple times but never in correct sequence."""
    keys = "static inline constexpr"
    # 'static' at positions 0, 3; 'inline' at 1; 'constexpr' at 4
    # No consecutive sequence of 'static inline constexpr' exists
    line = "static inline int static constexpr x;"
    result = check_key_sequence_ordered(keys, line)
    # Should be Error because the exact sequence isn't in correct consecutive order
    assert result.value == ResultTypeEnum.Error


def test_check_key_sequence_ordered_correct_order_not_consecutive() -> None:
    """Test when keys appear in correct order but not consecutively."""
    keys = "static inline constexpr"
    # Keys in order but with other tokens between them
    line = "static int inline float constexpr x = 42;"
    result = check_key_sequence_ordered(keys, line)
    # Should be Error because keys are not consecutively in order
    assert result.value == ResultTypeEnum.Error


def test_check_key_sequence_ordered_single_key() -> None:
    """Test with a single key."""
    keys = "static"
    line = "static int x = 42;"
    result = check_key_sequence_ordered(keys, line)
    assert result.value == ResultTypeEnum.Ok


def test_check_key_sequence_ordered_single_key_not_present() -> None:
    """Test with a single key that's not present."""
    keys = "static"
    line = "int x = 42;"
    result = check_key_sequence_ordered(keys, line)
    assert result.value == ResultTypeEnum.Ok


def test_check_key_sequence_ordered_partial_keys_present() -> None:
    """Test when only some keys from the sequence are present."""
    keys = "static inline constexpr"
    # Only 'static' and 'constexpr' are present, 'inline' is missing
    line = "static constexpr int x = 42;"
    result = check_key_sequence_ordered(keys, line)
    # Should return Ok since not all keys are present
    assert result.value == ResultTypeEnum.Ok
