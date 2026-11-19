"""Tests for devops.release.reviewers."""

from devops.release import extract_reviewers

URL = "https://github.com/MolarVerse/PQ/pull"


def test_unique_human_authors_in_order() -> None:
    """Bots, duplicates and other repositories are skipped."""
    notes = "\n".join(
        [
            "## What's Changed",
            f"* feat: a by @97gamjak in {URL}/1",
            f"* fix: b by @dependabot[bot] in {URL}/2",
            f"- fix: c by @ape33 in {URL}/3",
            f"* docs: d by @97gamjak in {URL}/4",
            "* other by @someone in https://github.com/Other/repo/pull/5",
            "* not an entry by @nobody",
        ]
    )
    assert extract_reviewers(notes, "MolarVerse/PQ") == ["97gamjak", "ape33"]


def test_no_entries_give_no_reviewers() -> None:
    """Empty notes give an empty list."""
    assert extract_reviewers("", "MolarVerse/PQ") == []
