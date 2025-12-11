"""Unit tests for file-related functionality in mstd checks."""

from devops.files import FileType


def test_all_types():

    expected_types = {
        FileType.CPPHeader,
        FileType.CPPSource,
        FileType.UNKNOWN,
        FileType.CMakeLists
    }

    actual_types = FileType.all_types()

    assert actual_types == expected_types, "FileType enum does not match expected types."
