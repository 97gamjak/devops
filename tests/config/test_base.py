"""Tests for devops.config.base module."""

import pytest

from devops.config.base import ConfigError, get_str_or_str_list


class TestGetStrOrStrList:
    """Tests for the get_str_or_str_list function."""

    def test_string_value(self) -> None:
        """Test that a string value is returned correctly."""
        mapping = {"key": "value"}
        result = get_str_or_str_list(mapping, "key")
        assert result == "value"
        assert isinstance(result, str)

    def test_list_of_strings(self) -> None:
        """Test that a list of strings is returned correctly."""
        mapping = {"key": ["value1", "value2", "value3"]}
        result = get_str_or_str_list(mapping, "key")
        assert result == ["value1", "value2", "value3"]
        assert isinstance(result, list)
        assert all(isinstance(item, str) for item in result)

    def test_empty_list_of_strings(self) -> None:
        """Test that an empty list of strings is returned correctly."""
        mapping = {"key": []}
        result = get_str_or_str_list(mapping, "key")
        assert result == []
        assert isinstance(result, list)

    def test_single_element_list(self) -> None:
        """Test that a single-element list is returned correctly."""
        mapping = {"key": ["single"]}
        result = get_str_or_str_list(mapping, "key")
        assert result == ["single"]
        assert isinstance(result, list)

    def test_mixed_list_with_non_strings(self) -> None:
        """Test that a list with non-string items raises ConfigError."""
        mapping = {"key": ["string", 123, "another"]}
        with pytest.raises(ConfigError) as exc_info:
            get_str_or_str_list(mapping, "key")

        assert "Expected str or list of str for key 'key'" in str(exc_info.value)
        assert "got list with non-string items" in str(exc_info.value)

    def test_list_with_only_integers(self) -> None:
        """Test that a list with only integers raises ConfigError."""
        mapping = {"key": [1, 2, 3]}
        with pytest.raises(ConfigError) as exc_info:
            get_str_or_str_list(mapping, "key")

        assert "Expected str or list of str for key 'key'" in str(exc_info.value)
        assert "got list with non-string items" in str(exc_info.value)

    def test_list_with_nested_list(self) -> None:
        """Test that a list with nested list raises ConfigError."""
        mapping = {"key": ["string", ["nested"]]}
        with pytest.raises(ConfigError) as exc_info:
            get_str_or_str_list(mapping, "key")

        assert "Expected str or list of str for key 'key'" in str(exc_info.value)
        assert "got list with non-string items" in str(exc_info.value)

    def test_integer_type(self) -> None:
        """Test that an integer type raises ConfigError."""
        mapping = {"key": 123}
        with pytest.raises(ConfigError) as exc_info:
            get_str_or_str_list(mapping, "key")

        assert "Expected str or list of str for key 'key'" in str(exc_info.value)
        assert "got int" in str(exc_info.value)

    def test_float_type(self) -> None:
        """Test that a float type raises ConfigError."""
        mapping = {"key": 3.14}
        with pytest.raises(ConfigError) as exc_info:
            get_str_or_str_list(mapping, "key")

        assert "Expected str or list of str for key 'key'" in str(exc_info.value)
        assert "got float" in str(exc_info.value)

    def test_dict_type(self) -> None:
        """Test that a dict type raises ConfigError."""
        mapping = {"key": {"nested": "value"}}
        with pytest.raises(ConfigError) as exc_info:
            get_str_or_str_list(mapping, "key")

        assert "Expected str or list of str for key 'key'" in str(exc_info.value)
        assert "got dict" in str(exc_info.value)

    def test_boolean_type(self) -> None:
        """Test that a boolean type raises ConfigError."""
        mapping = {"key": True}
        with pytest.raises(ConfigError) as exc_info:
            get_str_or_str_list(mapping, "key")

        assert "Expected str or list of str for key 'key'" in str(exc_info.value)
        assert "got bool" in str(exc_info.value)

    def test_missing_key_no_default(self) -> None:
        """Test that a missing key returns None when no default is provided."""
        mapping = {"other_key": "value"}
        result = get_str_or_str_list(mapping, "key")
        assert result is None

    def test_missing_key_with_string_default(self) -> None:
        """Test that a missing key returns the string default value."""
        mapping = {"other_key": "value"}
        result = get_str_or_str_list(mapping, "key", default="default_value")
        assert result == "default_value"
        assert isinstance(result, str)

    def test_missing_key_with_list_default(self) -> None:
        """Test that a missing key returns the list default value."""
        mapping = {"other_key": "value"}
        result = get_str_or_str_list(mapping, "key", default=["default1", "default2"])
        assert result == ["default1", "default2"]
        assert isinstance(result, list)

    def test_missing_key_with_none_default(self) -> None:
        """Test that a missing key returns None when None is explicitly set as default."""
        mapping = {"other_key": "value"}
        result = get_str_or_str_list(mapping, "key", default=None)
        assert result is None

    def test_none_value_with_default(self) -> None:
        """Test that an explicit None value returns None even with a default."""
        mapping = {"key": None}
        result = get_str_or_str_list(mapping, "key", default="default_value")
        assert result is None

    def test_none_value_no_default(self) -> None:
        """Test that an explicit None value returns None when no default is provided."""
        mapping = {"key": None}
        result = get_str_or_str_list(mapping, "key")
        assert result is None

    def test_empty_string(self) -> None:
        """Test that an empty string is returned correctly."""
        mapping = {"key": ""}
        result = get_str_or_str_list(mapping, "key")
        assert result == ""
        assert isinstance(result, str)

    def test_whitespace_string(self) -> None:
        """Test that a whitespace string is returned correctly."""
        mapping = {"key": "   "}
        result = get_str_or_str_list(mapping, "key")
        assert result == "   "
        assert isinstance(result, str)

    def test_string_with_special_characters(self) -> None:
        """Test that strings with special characters are handled correctly."""
        mapping = {"key": "path/to/file.txt"}
        result = get_str_or_str_list(mapping, "key")
        assert result == "path/to/file.txt"
        assert isinstance(result, str)

    def test_list_with_empty_strings(self) -> None:
        """Test that a list containing empty strings is handled correctly."""
        mapping = {"key": ["", "non-empty", ""]}
        result = get_str_or_str_list(mapping, "key")
        assert result == ["", "non-empty", ""]
        assert isinstance(result, list)
