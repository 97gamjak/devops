"""Tests for devops.config.base module."""

import pytest

from devops.config.base import ConfigError, get_str_or_str_list


class TestGetStrOrStrList:
    """Test cases for get_str_or_str_list function."""

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

    def test_empty_list(self) -> None:
        """Test that an empty list is handled correctly."""
        mapping = {"key": []}
        result = get_str_or_str_list(mapping, "key")
        assert result == []
        assert isinstance(result, list)

    def test_mixed_list_with_non_strings(self) -> None:
        """Test that a list with non-string items raises ConfigError."""
        mapping = {"key": ["string", 42, "another"]}
        
        with pytest.raises(ConfigError) as exc_info:
            get_str_or_str_list(mapping, "key")
        
        assert "Expected str or list of str for key 'key'" in str(exc_info.value)
        assert "got list with non-string items" in str(exc_info.value)

    def test_mixed_list_with_none(self) -> None:
        """Test that a list containing None raises ConfigError."""
        mapping = {"key": ["string", None, "another"]}
        
        with pytest.raises(ConfigError) as exc_info:
            get_str_or_str_list(mapping, "key")
        
        assert "Expected str or list of str for key 'key'" in str(exc_info.value)
        assert "got list with non-string items" in str(exc_info.value)

    def test_non_string_non_list_int(self) -> None:
        """Test that an integer value raises ConfigError."""
        mapping = {"key": 42}
        
        with pytest.raises(ConfigError) as exc_info:
            get_str_or_str_list(mapping, "key")
        
        assert "Expected str or list of str for key 'key'" in str(exc_info.value)
        assert "got int" in str(exc_info.value)

    def test_non_string_non_list_dict(self) -> None:
        """Test that a dict value raises ConfigError."""
        mapping = {"key": {"nested": "value"}}
        
        with pytest.raises(ConfigError) as exc_info:
            get_str_or_str_list(mapping, "key")
        
        assert "Expected str or list of str for key 'key'" in str(exc_info.value)
        assert "got dict" in str(exc_info.value)

    def test_non_string_non_list_bool(self) -> None:
        """Test that a boolean value raises ConfigError."""
        mapping = {"key": True}
        
        with pytest.raises(ConfigError) as exc_info:
            get_str_or_str_list(mapping, "key")
        
        assert "Expected str or list of str for key 'key'" in str(exc_info.value)
        assert "got bool" in str(exc_info.value)

    def test_missing_key_no_default(self) -> None:
        """Test that a missing key without default returns None."""
        mapping = {"other_key": "value"}
        result = get_str_or_str_list(mapping, "missing_key")
        assert result is None

    def test_missing_key_with_string_default(self) -> None:
        """Test that a missing key returns the string default value."""
        mapping = {"other_key": "value"}
        result = get_str_or_str_list(mapping, "missing_key", default="default_value")
        assert result == "default_value"
        assert isinstance(result, str)

    def test_missing_key_with_list_default(self) -> None:
        """Test that a missing key returns the list default value."""
        mapping = {"other_key": "value"}
        result = get_str_or_str_list(mapping, "missing_key", default=["default1", "default2"])
        assert result == ["default1", "default2"]
        assert isinstance(result, list)

    def test_missing_key_with_none_default(self) -> None:
        """Test that a missing key with None default returns None."""
        mapping = {"other_key": "value"}
        result = get_str_or_str_list(mapping, "missing_key", default=None)
        assert result is None

    def test_explicit_none_value(self) -> None:
        """Test that an explicit None value in mapping returns None."""
        mapping = {"key": None}
        result = get_str_or_str_list(mapping, "key")
        assert result is None

    def test_explicit_none_value_with_default(self) -> None:
        """Test that an explicit None value returns None even with default."""
        mapping = {"key": None}
        result = get_str_or_str_list(mapping, "key", default="default_value")
        assert result is None

    def test_empty_string(self) -> None:
        """Test that an empty string is handled correctly."""
        mapping = {"key": ""}
        result = get_str_or_str_list(mapping, "key")
        assert result == ""
        assert isinstance(result, str)

    def test_single_item_list(self) -> None:
        """Test that a single-item list is returned correctly."""
        mapping = {"key": ["single"]}
        result = get_str_or_str_list(mapping, "key")
        assert result == ["single"]
        assert isinstance(result, list)
