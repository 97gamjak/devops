"""Tests for devops.git.tag module."""

import subprocess
from dataclasses import FrozenInstanceError
from unittest.mock import ANY, MagicMock, patch

import pytest

from devops.git.tag import GitTag, GitTagError, get_all_tags, get_latest_tag


class TestGitTag:
    """Test cases for the GitTag class."""

    def test_str_representation(self) -> None:
        """Test string representation of GitTag."""
        tag = GitTag(1, 2, 3)
        assert str(tag) == "v1.2.3"

    def test_str_representation_with_zeros(self) -> None:
        """Test string representation with zero values."""
        tag = GitTag(0, 0, 0)
        assert str(tag) == "v0.0.0"

    def test_str_representation_with_large_numbers(self) -> None:
        """Test string representation with large version numbers."""
        tag = GitTag(10, 20, 30)
        assert str(tag) == "v10.20.30"

    def test_from_string_with_v_prefix(self) -> None:
        """Test creating GitTag from string with 'v' prefix."""
        tag = GitTag.from_string("v1.2.3")
        assert tag.major == 1
        assert tag.minor == 2
        assert tag.patch == 3

    def test_from_string_without_v_prefix(self) -> None:
        """Test creating GitTag from string without 'v' prefix."""
        tag = GitTag.from_string("1.2.3")
        assert tag.major == 1
        assert tag.minor == 2
        assert tag.patch == 3

    def test_from_string_with_zeros(self) -> None:
        """Test creating GitTag from string with zero values."""
        tag = GitTag.from_string("v0.0.0")
        assert tag.major == 0
        assert tag.minor == 0
        assert tag.patch == 0

    def test_from_string_with_large_numbers(self) -> None:
        """Test creating GitTag from string with large version numbers."""
        tag = GitTag.from_string("v10.20.30")
        assert tag.major == 10
        assert tag.minor == 20
        assert tag.patch == 30

    def test_from_string_with_too_few_parts(self) -> None:
        """Test from_string raises error with too few version parts."""
        with pytest.raises(GitTagError) as exc_info:
            GitTag.from_string("v1.2")

        assert "Invalid tag format: v1.2" in str(exc_info.value)

    def test_from_string_with_too_many_parts(self) -> None:
        """Test from_string raises error with too many version parts."""
        with pytest.raises(GitTagError) as exc_info:
            GitTag.from_string("v1.2.3.4")

        assert "Invalid tag format: v1.2.3.4" in str(exc_info.value)

    def test_from_string_with_non_numeric_major(self) -> None:
        """Test from_string raises error with non-numeric major version."""
        with pytest.raises(GitTagError) as exc_info:
            GitTag.from_string("va.2.3")

        assert "Invalid numeric components in tag: va.2.3" in str(exc_info.value)

    def test_from_string_with_non_numeric_minor(self) -> None:
        """Test from_string raises error with non-numeric minor version."""
        with pytest.raises(GitTagError) as exc_info:
            GitTag.from_string("v1.b.3")

        assert "Invalid numeric components in tag: v1.b.3" in str(exc_info.value)

    def test_from_string_with_non_numeric_patch(self) -> None:
        """Test from_string raises error with non-numeric patch version."""
        with pytest.raises(GitTagError) as exc_info:
            GitTag.from_string("v1.2.c")

        assert "Invalid numeric components in tag: v1.2.c" in str(exc_info.value)

    def test_from_string_with_empty_string(self) -> None:
        """Test from_string raises error with empty string."""
        with pytest.raises(GitTagError) as exc_info:
            GitTag.from_string("")

        assert "Invalid tag format:" in str(exc_info.value)

    def test_from_string_with_only_v(self) -> None:
        """Test from_string raises error with only 'v' character."""
        with pytest.raises(GitTagError) as exc_info:
            GitTag.from_string("v")

        assert "Invalid tag format: v" in str(exc_info.value)

    def test_ordering_equal_tags(self) -> None:
        """Test ordering of equal tags."""
        tag1 = GitTag(1, 2, 3)
        tag2 = GitTag(1, 2, 3)
        assert tag1 == tag2
        assert not tag1 < tag2
        assert not tag1 > tag2

    def test_ordering_different_major(self) -> None:
        """Test ordering based on major version."""
        tag1 = GitTag(1, 2, 3)
        tag2 = GitTag(2, 2, 3)
        assert tag1 < tag2
        assert tag2 > tag1

    def test_ordering_different_minor(self) -> None:
        """Test ordering based on minor version."""
        tag1 = GitTag(1, 2, 3)
        tag2 = GitTag(1, 3, 3)
        assert tag1 < tag2
        assert tag2 > tag1

    def test_ordering_different_patch(self) -> None:
        """Test ordering based on patch version."""
        tag1 = GitTag(1, 2, 3)
        tag2 = GitTag(1, 2, 4)
        assert tag1 < tag2
        assert tag2 > tag1

    def test_ordering_multiple_tags(self) -> None:
        """Test sorting multiple tags."""
        tags = [
            GitTag(2, 0, 0),
            GitTag(1, 0, 0),
            GitTag(1, 2, 0),
            GitTag(1, 1, 0),
            GitTag(1, 1, 5),
        ]
        sorted_tags = sorted(tags)
        assert sorted_tags == [
            GitTag(1, 0, 0),
            GitTag(1, 1, 0),
            GitTag(1, 1, 5),
            GitTag(1, 2, 0),
            GitTag(2, 0, 0),
        ]

    def test_max_tag(self) -> None:
        """Test finding max tag from list."""
        tags = [GitTag(1, 0, 0), GitTag(2, 5, 3), GitTag(2, 5, 1)]
        assert max(tags) == GitTag(2, 5, 3)

    def test_frozen_dataclass(self) -> None:
        """Test that GitTag is immutable."""
        tag = GitTag(1, 2, 3)
        with pytest.raises(FrozenInstanceError, match="cannot assign to field"):
            tag.major = 5  # type: ignore[misc]


class TestGetAllTags:
    """Test cases for the get_all_tags function."""

    @patch("devops.git.tag.subprocess.check_output")
    def test_get_all_tags_with_multiple_tags(
        self, mock_check_output: MagicMock
    ) -> None:
        """Test retrieving multiple tags from repository."""
        mock_check_output.return_value = "v1.0.0\nv1.1.0\nv2.0.0\n"

        tags = get_all_tags()

        assert len(tags) == 3
        assert tags[0] == GitTag(1, 0, 0)
        assert tags[1] == GitTag(1, 1, 0)
        assert tags[2] == GitTag(2, 0, 0)
        mock_check_output.assert_called_once_with(
            ["git", "tag", "--list"],
            stderr=ANY,
            text=True,
        )

    @patch("devops.git.tag.subprocess.check_output")
    def test_get_all_tags_with_single_tag(self, mock_check_output: MagicMock) -> None:
        """Test retrieving single tag from repository."""
        mock_check_output.return_value = "v1.0.0\n"

        tags = get_all_tags()

        assert len(tags) == 1
        assert tags[0] == GitTag(1, 0, 0)

    @patch("devops.git.tag.subprocess.check_output")
    def test_get_all_tags_with_empty_repository(
        self, mock_check_output: MagicMock
    ) -> None:
        """Test retrieving tags from empty repository."""
        mock_check_output.return_value = ""

        tags = get_all_tags()

        assert len(tags) == 0
        assert tags == []

    @patch("devops.git.tag.subprocess.check_output")
    def test_get_all_tags_with_whitespace_only(
        self, mock_check_output: MagicMock
    ) -> None:
        """Test retrieving tags when output is only whitespace."""
        mock_check_output.return_value = "   \n\n   "

        tags = get_all_tags()

        assert len(tags) == 0
        assert tags == []

    @patch("devops.git.tag.subprocess.check_output")
    def test_get_all_tags_subprocess_error_allowed(
        self, mock_check_output: MagicMock
    ) -> None:
        """Test get_all_tags returns empty list on subprocess error when allowed."""
        mock_check_output.side_effect = subprocess.CalledProcessError(1, "git")

        tags = get_all_tags(empty_tag_list_allowed=True)

        assert tags == []

    @patch("devops.git.tag.subprocess.check_output")
    def test_get_all_tags_subprocess_error_not_allowed(
        self, mock_check_output: MagicMock
    ) -> None:
        """Test get_all_tags raises error on subprocess error when not allowed."""
        mock_check_output.side_effect = subprocess.CalledProcessError(1, "git")

        with pytest.raises(GitTagError) as exc_info:
            get_all_tags(empty_tag_list_allowed=False)

        assert "Failed to retrieve Git tags" in str(exc_info.value)

    @patch("devops.git.tag.subprocess.check_output")
    def test_get_all_tags_with_invalid_tag_format(
        self, mock_check_output: MagicMock
    ) -> None:
        """Test get_all_tags raises error with invalid tag format."""
        mock_check_output.return_value = "v1.0.0\ninvalid-tag\nv2.0.0\n"

        with pytest.raises(GitTagError) as exc_info:
            get_all_tags()

        assert "Invalid tag format: invalid-tag" in str(exc_info.value)

    @patch("devops.git.tag.subprocess.check_output")
    def test_get_all_tags_without_v_prefix(self, mock_check_output: MagicMock) -> None:
        """Test get_all_tags handles tags without 'v' prefix."""
        mock_check_output.return_value = "1.0.0\n2.0.0\n"

        tags = get_all_tags()

        assert len(tags) == 2
        assert tags[0] == GitTag(1, 0, 0)
        assert tags[1] == GitTag(2, 0, 0)

    @patch("devops.git.tag.subprocess.check_output")
    def test_get_all_tags_mixed_prefix(self, mock_check_output: MagicMock) -> None:
        """Test get_all_tags handles mixed prefix tags."""
        mock_check_output.return_value = "v1.0.0\n2.0.0\nv3.0.0\n"

        tags = get_all_tags()

        assert len(tags) == 3
        assert tags[0] == GitTag(1, 0, 0)
        assert tags[1] == GitTag(2, 0, 0)
        assert tags[2] == GitTag(3, 0, 0)


class TestGetLatestTag:
    """Test cases for the get_latest_tag function."""

    @patch("devops.git.tag.subprocess.check_output")
    def test_get_latest_tag_with_multiple_tags(
        self, mock_check_output: MagicMock
    ) -> None:
        """Test getting latest tag from multiple tags."""
        mock_check_output.return_value = "v1.0.0\nv2.5.3\nv2.5.1\nv1.9.9\n"

        latest = get_latest_tag()

        assert latest == GitTag(2, 5, 3)

    @patch("devops.git.tag.subprocess.check_output")
    def test_get_latest_tag_with_single_tag(self, mock_check_output: MagicMock) -> None:
        """Test getting latest tag when only one tag exists."""
        mock_check_output.return_value = "v1.0.0\n"

        latest = get_latest_tag()

        assert latest == GitTag(1, 0, 0)

    @patch("devops.git.tag.subprocess.check_output")
    def test_get_latest_tag_with_no_tags(self, mock_check_output: MagicMock) -> None:
        """Test getting latest tag from empty repository returns default tag."""
        mock_check_output.return_value = ""

        latest = get_latest_tag()

        assert latest == GitTag(0, 0, 0)

    @patch("devops.git.tag.subprocess.check_output")
    def test_get_latest_tag_ordering_by_major(
        self, mock_check_output: MagicMock
    ) -> None:
        """Test latest tag is determined by major version."""
        mock_check_output.return_value = "v1.9.9\nv2.0.0\nv1.10.10\n"

        latest = get_latest_tag()

        assert latest == GitTag(2, 0, 0)

    @patch("devops.git.tag.subprocess.check_output")
    def test_get_latest_tag_ordering_by_minor(
        self, mock_check_output: MagicMock
    ) -> None:
        """Test latest tag is determined by minor version when major is same."""
        mock_check_output.return_value = "v1.5.9\nv1.10.0\nv1.9.10\n"

        latest = get_latest_tag()

        assert latest == GitTag(1, 10, 0)

    @patch("devops.git.tag.subprocess.check_output")
    def test_get_latest_tag_ordering_by_patch(
        self, mock_check_output: MagicMock
    ) -> None:
        """Test latest tag by patch version when major and minor are same."""
        mock_check_output.return_value = "v1.5.9\nv1.5.15\nv1.5.10\n"

        latest = get_latest_tag()

        assert latest == GitTag(1, 5, 15)


class TestGitTagError:
    """Test cases for the GitTagError exception."""

    def test_git_tag_error_message(self) -> None:
        """Test GitTagError formats message correctly."""
        error = GitTagError("Test error message")
        assert str(error) == "GitTagError: Test error message"
        assert error.message == "Test error message"

    def test_git_tag_error_inheritance(self) -> None:
        """Test GitTagError inherits from Exception."""
        error = GitTagError("Test error")
        assert isinstance(error, Exception)

    def test_git_tag_error_can_be_raised(self) -> None:
        """Test GitTagError can be raised and caught."""
        msg = "Test error"
        with pytest.raises(GitTagError) as exc_info:
            raise GitTagError(msg)

        assert "Test error" in str(exc_info.value)
