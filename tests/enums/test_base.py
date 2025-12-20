"""Tests for devops.enums.base module."""

import pytest

from devops.enums.base import StrEnum


class SampleEnum(StrEnum):
    """Test enumeration for testing StrEnum functionality."""

    OPTION_A = "OPTION_A"
    OPTION_B = "OPTION_B"
    OPTION_C = "OPTION_C"


def test_str_enum_str_representation() -> None:
    """Test string representation of StrEnum members."""
    assert str(SampleEnum.OPTION_A) == "OPTION_A"
    assert str(SampleEnum.OPTION_B) == "OPTION_B"
    assert str(SampleEnum.OPTION_C) == "OPTION_C"


def test_str_enum_case_insensitive_access() -> None:
    """Test case-insensitive access to StrEnum members."""
    assert SampleEnum("option_a") == SampleEnum.OPTION_A
    assert SampleEnum("OPTION_A") == SampleEnum.OPTION_A
    assert SampleEnum("Option_A") == SampleEnum.OPTION_A
    assert SampleEnum("option_b") == SampleEnum.OPTION_B
    assert SampleEnum("OPTION_B") == SampleEnum.OPTION_B


def test_str_enum_invalid_value() -> None:
    """Test that invalid values raise ValueError."""
    with pytest.raises(ValueError):
        SampleEnum("invalid_option")

    with pytest.raises(ValueError):
        SampleEnum("OPTION_D")


def test_str_enum_is_valid_with_valid_values() -> None:
    """Test is_valid method with valid enumeration values."""
    assert SampleEnum.is_valid("OPTION_A") is True
    assert SampleEnum.is_valid("option_a") is True
    assert SampleEnum.is_valid("Option_A") is True
    assert SampleEnum.is_valid("OPTION_B") is True
    assert SampleEnum.is_valid("option_b") is True
    assert SampleEnum.is_valid("OPTION_C") is True
    assert SampleEnum.is_valid("option_c") is True


def test_str_enum_is_valid_with_invalid_values() -> None:
    """Test is_valid method with invalid values."""
    assert SampleEnum.is_valid("invalid") is False
    assert SampleEnum.is_valid("OPTION_D") is False
    assert SampleEnum.is_valid("") is False
    assert SampleEnum.is_valid("option") is False


def test_str_enum_list_values() -> None:
    """Test list_values method returns all enumeration values."""
    values = SampleEnum.list_values()

    assert isinstance(values, list)
    assert len(values) == 3
    assert "OPTION_A" in values
    assert "OPTION_B" in values
    assert "OPTION_C" in values


def test_str_enum_list_values_order() -> None:
    """Test that list_values preserves enum definition order."""
    values = SampleEnum.list_values()

    assert values[0] == "OPTION_A"
    assert values[1] == "OPTION_B"
    assert values[2] == "OPTION_C"


def test_str_enum_list_values_returns_new_list() -> None:
    """Test that list_values returns a new list each time."""
    values1 = SampleEnum.list_values()
    values2 = SampleEnum.list_values()

    assert values1 == values2
    assert values1 is not values2
