"""Unit tests for file-related functionality in mstd checks."""

from devops.files import FileType


def test_all_types() -> None:
    """Test that FileType.all_types() returns the expected set of file types."""
    expected_types = {
        FileType.CPPHeader,
        FileType.CPPSource,
        FileType.UNKNOWN,
        FileType.CMakeLists,
    }

    actual_types = FileType.all_types()

    assert actual_types == expected_types
