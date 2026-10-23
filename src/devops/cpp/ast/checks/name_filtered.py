"""Shared base for checks that can be narrowed by name via TOML.

A `NameFilteredCheck` reads two optional lists from its
``[cpp.ast_check_config.<id>]`` table::

    enabled_names  = ["std"]              # allowlist; empty/unset = everything
    disabled_names = ["std::literals"]    # always skipped, wins over enabled_names

Names are matched exactly against the qualified name as written in the
source; a leading ``::`` is ignored.

Per-name path exceptions allow specific names to pass through in designated
files or directories.  Each entry names the exempt names and the file-path
patterns where they are allowed::

    [[cpp.ast_check_config.<id>.path_exceptions]]
    names = ["rad"]
    paths = ["src/units/", "include/units/"]

Patterns ending with ``/`` match any file whose path starts with that
prefix (recursively).  Any other pattern is matched using ``fnmatch`` rules
(``*`` matches within a directory component, ``?`` matches one character).
"""

from __future__ import annotations

import fnmatch
from dataclasses import dataclass

from devops.config.base import ConfigError
from devops.cpp.ast.base import Check


@dataclass(frozen=True)
class PathException:
    """A set of names that are allowed only in specific file paths."""

    names: frozenset[str]
    paths: tuple[str, ...]


def _matches_path(filename: str, pattern: str) -> bool:
    """Return True if *filename* matches *pattern*.

    Patterns ending with ``/`` are treated as directory prefixes: any file
    whose path starts with the pattern is a match (covering all subdirectories).
    All other patterns are matched with :func:`fnmatch.fnmatch`.
    """
    if pattern.endswith("/"):
        return filename.startswith(pattern)
    return fnmatch.fnmatch(filename, pattern)


class NameFilteredCheck(Check):
    """Check base class providing ``enabled_names`` / ``disabled_names`` filtering."""

    def __init__(self) -> None:
        """Initialise with no name filtering (every name is selected)."""
        self.enabled_names: frozenset[str] = frozenset()
        self.disabled_names: frozenset[str] = frozenset()
        self.path_exceptions: list[PathException] = []

    def configure(self, config: dict) -> None:
        """Load the name allow/deny lists from the check's TOML config block.

        Parameters
        ----------
        config: dict
            Expected shape: ``{"enabled_names": ["std"], "disabled_names":
            ["std::literals"], "path_exceptions": [{"names": ["rad"],
            "paths": ["src/units/"]}]}``. All keys are optional.

        Raises
        ------
        ConfigError
            If any key is present but has an invalid type.

        """
        self.enabled_names = self._parse_names(config, "enabled_names")
        self.disabled_names = self._parse_names(config, "disabled_names")
        self.path_exceptions = self._parse_path_exceptions(config)

    def _parse_names(self, config: dict, key: str) -> frozenset[str]:
        raw = config.get(key, [])
        if not isinstance(raw, list) or not all(isinstance(n, str) for n in raw):
            msg = (
                f"{self.id}: '{key}' in [cpp.ast_check_config.{self.id}] "
                "must be a list of strings"
            )
            raise ConfigError(msg)
        return frozenset(n.removeprefix("::") for n in raw)

    def _parse_path_exceptions(self, config: dict) -> list[PathException]:
        raw = config.get("path_exceptions", [])
        if not isinstance(raw, list):
            msg = (
                f"{self.id}: 'path_exceptions' in [cpp.ast_check_config.{self.id}] "
                "must be an array of tables"
            )
            raise ConfigError(msg)
        exceptions = []
        for i, entry in enumerate(raw):
            if not isinstance(entry, dict):
                msg = (
                    f"{self.id}: 'path_exceptions[{i}]' in "
                    f"[cpp.ast_check_config.{self.id}] must be a table"
                )
                raise ConfigError(msg)

            names_raw = entry.get("names", [])
            if not isinstance(names_raw, list) or not all(
                isinstance(n, str) for n in names_raw
            ):
                msg = (
                    f"{self.id}: 'path_exceptions[{i}].names' in "
                    f"[cpp.ast_check_config.{self.id}] must be a list of strings"
                )
                raise ConfigError(msg)
            names = frozenset(n.removeprefix("::") for n in names_raw)

            paths_raw = entry.get("paths", [])
            if not isinstance(paths_raw, list) or not all(
                isinstance(p, str) for p in paths_raw
            ):
                msg = (
                    f"{self.id}: 'path_exceptions[{i}].paths' in "
                    f"[cpp.ast_check_config.{self.id}] must be a list of strings"
                )
                raise ConfigError(msg)

            exceptions.append(PathException(names=names, paths=tuple(paths_raw)))
        return exceptions

    def _is_selected(self, name: str) -> bool:
        """Return whether `name` should be reported given the name filters."""
        name = name.removeprefix("::")
        if self.enabled_names and name not in self.enabled_names:
            return False
        return name not in self.disabled_names

    def _is_selected_for_file(self, name: str, filename: str) -> bool:
        """Return whether `name` in `filename` should be reported.

        Applies the name filters first; then checks whether any
        ``path_exceptions`` entry exempts this name for the given file.

        Parameters
        ----------
        name: str
            The qualified name as written in the source.
        filename: str
            Path of the file being checked.

        Returns
        -------
        bool
            True if the name should be reported, False if it is allowed.

        """
        if not self._is_selected(name):
            return False
        clean = name.removeprefix("::")
        for exc in self.path_exceptions:
            if clean in exc.names and any(
                _matches_path(filename, pat) for pat in exc.paths
            ):
                return False
        return True
