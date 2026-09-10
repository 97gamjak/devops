"""Tests for devops.cpp.ast.registry.select_checks and configure_checks."""

from __future__ import annotations

import pytest

from devops.cpp.ast.base import Check
from devops.cpp.ast.registry import configure_checks, select_checks


class _FakeCheck(Check):
    """Minimal Check stand-in for exercising select_checks/configure_checks."""

    def __init__(self, check_id: str) -> None:
        """Initialize with a fixed id."""
        self.id = check_id
        self.received_config: dict | None = None

    def configure(self, config: dict) -> None:
        """Record the config dict passed in."""
        self.received_config = config


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


class TestConfigureChecks:
    """Tests for configure_checks."""

    def test_no_config_returns_same_checks(self, checks: list[Check]) -> None:
        """With no check_config, the original check instances are returned."""
        result = configure_checks(checks)
        assert result == checks

    def test_known_id_receives_config(self, checks: list[Check]) -> None:
        """A check whose id is in check_config gets configure() called.

        Parameters
        ----------
        checks: list[Check]
            Fixture providing three fake checks with ids 'a', 'b', 'c'.

        """
        result = configure_checks(checks, {"b": {"key": "value"}})
        b_check = next(c for c in result if c.id == "b")
        assert isinstance(b_check, _FakeCheck)
        assert b_check.received_config == {"key": "value"}

    def test_original_not_mutated(self, checks: list[Check]) -> None:
        """configure_checks works on a shallow copy; original is untouched.

        Parameters
        ----------
        checks: list[Check]
            Fixture providing three fake checks with ids 'a', 'b', 'c'.

        """
        original_b = next(c for c in checks if c.id == "b")
        configure_checks(checks, {"b": {"key": "value"}})
        assert isinstance(original_b, _FakeCheck)
        assert original_b.received_config is None

    def test_unknown_check_id_in_config_is_ignored(self, checks: list[Check]) -> None:
        """Config entries whose id matches no check are silently ignored.

        Parameters
        ----------
        checks: list[Check]
            Fixture providing three fake checks with ids 'a', 'b', 'c'.

        """
        result = configure_checks(checks, {"does-not-exist": {"x": 1}})
        assert [c.id for c in result] == ["a", "b", "c"]

    def test_unconfigured_checks_pass_through_unchanged(
        self, checks: list[Check]
    ) -> None:
        """Checks not in check_config are returned as-is (not copied).

        Parameters
        ----------
        checks: list[Check]
            Fixture providing three fake checks with ids 'a', 'b', 'c'.

        """
        result = configure_checks(checks, {"b": {}})
        a_result = next(c for c in result if c.id == "a")
        a_original = next(c for c in checks if c.id == "a")
        assert a_result is a_original
