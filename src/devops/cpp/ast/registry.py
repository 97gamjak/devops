"""Registry of active AST checks.

Add a new check here after implementing it as a `Check` subclass under
`devops.cpp.ast.checks`.
"""

from __future__ import annotations

import copy
import typing

from devops.cpp.ast.checks.enforce_param_name_for_type import EnforceParamNameForType
from devops.cpp.ast.checks.no_global_using import NoGlobalUsing
from devops.cpp.ast.checks.no_global_using_enum import NoGlobalUsingEnum
from devops.logger import cpp_check_logger

if typing.TYPE_CHECKING:
    from devops.cpp.ast.base import Check

# NOTE: register future checks here by importing the Check subclass above
# and adding an instance below.
# Each check's `.id` is the identifier used in CppConfig.ast_check_enabled_ids
# / ast_check_disabled_ids to turn it on or off from the input file.
ALL_CHECKS: list[Check] = [
    EnforceParamNameForType(),
    NoGlobalUsing(),
    NoGlobalUsingEnum(),
]


def select_checks(
    checks: list[Check],
    *,
    enabled_ids: list[str] | None = None,
    disabled_ids: list[str] | None = None,
) -> list[Check]:
    """Filter checks by id using an optional allow/deny list.

    An empty (or omitted) `enabled_ids` means "no allowlist restriction" —
    every check runs except those in `disabled_ids`. A non-empty
    `enabled_ids` acts as an allowlist: only those checks run, and
    `disabled_ids` is still subtracted from that set.

    Parameters
    ----------
    checks: list[Check]
        The checks to filter, typically `ALL_CHECKS`.
    enabled_ids: list[str] | None
        If non-empty, only checks whose `.id` is in this list are kept.
    disabled_ids: list[str] | None
        Checks whose `.id` is in this list are always dropped.

    Returns
    -------
    list[Check]
        The filtered list of checks.

    """
    known_ids = {check.id for check in checks}
    enabled_ids = enabled_ids or []
    disabled_ids = disabled_ids or []

    for check_id in [*enabled_ids, *disabled_ids]:
        if check_id not in known_ids:
            cpp_check_logger.warning(
                f"Unknown AST check id '{check_id}' in "
                "ast_check_enabled_ids/ast_check_disabled_ids. "
                f"Known ids: {sorted(known_ids)}"
            )

    disabled = set(disabled_ids)

    if enabled_ids:
        allowed = set(enabled_ids)
        return [c for c in checks if c.id in allowed and c.id not in disabled]

    return [c for c in checks if c.id not in disabled]


def configure_checks(
    checks: list[Check],
    check_config: dict[str, dict] | None = None,
) -> list[Check]:
    """Apply per-check configuration and return a new list of checks.

    Each check whose `.id` appears in `check_config` receives a shallow
    copy so that the shared `ALL_CHECKS` singletons are never mutated.

    Parameters
    ----------
    checks: list[Check]
        The checks to configure, typically the result of `select_checks`.
    check_config: dict[str, dict] | None
        Mapping of check id → raw config dict (the sub-table from
        ``cpp.ast_check_config.<id>`` in the project TOML). Unknown ids
        are silently ignored.

    Returns
    -------
    list[Check]
        A new list where configured checks are shallow-copied instances.

    """
    if not check_config:
        return list(checks)
    result: list[Check] = []
    for check in checks:
        if check.id in check_config:
            configured = copy.copy(check)
            configured.configure(check_config[check.id])
            result.append(configured)
        else:
            result.append(check)
    return result
