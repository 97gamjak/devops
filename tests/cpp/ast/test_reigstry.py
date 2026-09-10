"""Tests for devops.cpp.ast.registry.select_checks."""

from __future__ import annotations

import pytest

from devops.cpp.ast.base import Check
from devops.cpp.ast.registry import select_checks


class _FakeCheck(Check):
    """Minimal Check stand-in for exercising select_checks in isolation."""

    def __init__(self, check_id: str) -> None:
        """Initialize with a fixed id."""
        self.id = check_id


@pytest.fixture
def checks() -> list[Check]:
    """Three fake checks with distinct ids."""
    return [_FakeCheck("a"), _FakeCheck("b"), _FakeCheck("c")]


class TestSelectChecks:
    """Tests for select_checks."""

    def test_no_filters_returns_all(self, checks: list[Check]) -> None:
        """With no enabled/disabled ids, every check is kept."""
        assert select_checks(checks) == checks

    def test_disabled_id_is_removed(self, checks: list[Check]) -> None:
        """A disabled id is dropped, others are kept."""
        result = select_checks(checks, disabled_ids=["b"])
        assert [c.id for c in result] == ["a", "c"]

    def test_enabled_ids_act_as_allowlist(self, checks: list[Check]) -> None:
        """A non-empty enabled list keeps only those ids."""
        result = select_checks(checks, enabled_ids=["a"])
        assert [c.id for c in result] == ["a"]

    def test_disabled_overrides_enabled_for_same_id(self, checks: list[Check]) -> None:
        """Disabling an id that's also enabled still excludes it."""
        result = select_checks(checks, enabled_ids=["a", "b"], disabled_ids=["b"])
        assert [c.id for c in result] == ["a"]

    def test_empty_enabled_list_means_no_restriction(self, checks: list[Check]) -> None:
        """An empty enabled list is treated as 'no allowlist', not 'none'."""
        result = select_checks(checks, enabled_ids=[])
        assert [c.id for c in result] == ["a", "b", "c"]

    def test_unknown_id_logs_warning(
        self, checks: list[Check], caplog: pytest.LogCaptureFixture
    ) -> None:
        """An id that matches no known check logs a warning."""
        select_checks(checks, disabled_ids=["does-not-exist"])

        assert any(
            "Unknown AST check id" in record.message for record in caplog.records
        )
