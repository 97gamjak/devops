"""Shared base for checks that can be narrowed by name via TOML.

A `NameFilteredCheck` reads two optional lists from its
``[cpp.ast_check_config.<id>]`` table::

    enabled_names  = ["std"]              # allowlist; empty/unset = everything
    disabled_names = ["std::literals"]    # always skipped, wins over enabled_names

Names are matched exactly against the qualified name as written in the
source; a leading ``::`` is ignored.
"""

from __future__ import annotations

from devops.config.base import ConfigError
from devops.cpp.ast.base import Check


class NameFilteredCheck(Check):
    """Check base class providing ``enabled_names`` / ``disabled_names`` filtering."""

    def __init__(self) -> None:
        """Initialise with no name filtering (every name is selected)."""
        self.enabled_names: frozenset[str] = frozenset()
        self.disabled_names: frozenset[str] = frozenset()

    def configure(self, config: dict) -> None:
        """Load the name allow/deny lists from the check's TOML config block.

        Parameters
        ----------
        config: dict
            Expected shape: ``{"enabled_names": ["std"], "disabled_names":
            ["std::literals"]}``. Both keys are optional lists of strings.

        Raises
        ------
        ConfigError
            If either key is present but is not a list of strings.

        """
        self.enabled_names = self._parse_names(config, "enabled_names")
        self.disabled_names = self._parse_names(config, "disabled_names")

    def _parse_names(self, config: dict, key: str) -> frozenset[str]:
        raw = config.get(key, [])
        if not isinstance(raw, list) or not all(isinstance(n, str) for n in raw):
            msg = (
                f"{self.id}: '{key}' in [cpp.ast_check_config.{self.id}] "
                "must be a list of strings"
            )
            raise ConfigError(msg)
        return frozenset(n.removeprefix("::") for n in raw)

    def _is_selected(self, name: str) -> bool:
        """Return whether `name` should be reported given the name filters."""
        name = name.removeprefix("::")
        if self.enabled_names and name not in self.enabled_names:
            return False
        return name not in self.disabled_names
