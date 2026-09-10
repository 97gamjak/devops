"""Registry of active AST checks.

Add a new check here after implementing it as a `Check` subclass under
`devops.cpp.ast.checks`.
"""

from __future__ import annotations

import typing

from devops.cpp.ast.checks.enforce_param_name_for_type import EnforceParamNameForType
from devops.logger import cpp_check_logger

if typing.TYPE_CHECKING:
    from devops.cpp.ast.base import Check

# NOTE: register future checks (e.g. a migrated no_global_using_enum) here
# by importing the Check subclass above and adding an instance below.
# Each check's `.id` is the identifier used in CppConfig.ast_check_enabled_ids
# / ast_check_disabled_ids to turn it on or off from the input file.
ALL_CHECKS: list[Check] = [
    EnforceParamNameForType(),
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
