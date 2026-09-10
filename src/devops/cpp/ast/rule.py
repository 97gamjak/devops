"""Rule adapter exposing the AST-check engine through devops's Rule interface."""

from __future__ import annotations

import typing

from devops.cpp.ast.engine import run_ast_checks
from devops.cpp.ast.registry import ALL_CHECKS, configure_checks, select_checks
from devops.rules import ResultType, ResultTypeEnum, Rule, RuleInputType, RuleType

if typing.TYPE_CHECKING:
    from devops.rules import FileRuleInput

DEFAULT_COMPILE_ARGS = ["-std=c++23"]


class ASTChecksRule(Rule):
    """Run every enabled libclang AST-based check in a single pass.

    Slots into `build_cpp_rules` as one ordinary FILE rule: each file is
    parsed once by libclang, and every enabled check in
    `devops.cpp.ast.registry.ALL_CHECKS` is dispatched against that single
    AST walk. All diagnostics found are combined into one ResultType.
    """

    def __init__(
        self,
        compile_args: list[str] | None = None,
        enabled_check_ids: list[str] | None = None,
        disabled_check_ids: list[str] | None = None,
        check_config: dict[str, dict] | None = None,
    ) -> None:
        """Initialize ASTChecksRule.

        Parameters
        ----------
        compile_args: list[str] | None
            Compiler flags passed to libclang when parsing each file.
            Defaults to `DEFAULT_COMPILE_ARGS`.
        enabled_check_ids: list[str] | None
            If non-empty, only checks whose `.id` is in this list run
            (see `devops.cpp.ast.registry.select_checks`).
        disabled_check_ids: list[str] | None
            Checks whose `.id` is in this list never run.
        check_config: dict[str, dict] | None
            Per-check configuration keyed by check id (from
            ``cpp.ast_check_config`` in the project TOML). Passed to
            each check's ``configure()`` method.

        """
        self.compile_args = compile_args or DEFAULT_COMPILE_ARGS
        self.checks = configure_checks(
            select_checks(
                ALL_CHECKS,
                enabled_ids=enabled_check_ids,
                disabled_ids=disabled_check_ids,
            ),
            check_config,
        )

        super().__init__(
            name="ASTChecks",
            description="Run all enabled libclang AST-based C++ checks.",
            rule_type=RuleType.CPP_STYLE,
            rule_input_type=RuleInputType.FILE,
            func=self._run,
        )

    def _run(self, file_rule_input: FileRuleInput) -> ResultType:
        """Run all enabled AST checks against a single file.

        Parameters
        ----------
        file_rule_input: FileRuleInput
            The file content and path to check.

        Returns
        -------
        ResultType
            Ok if no check reported anything; otherwise an Error whose
            description lists every diagnostic found, one per line.

        """
        if file_rule_input.path is None:
            return ResultType(ResultTypeEnum.Ok)

        diagnostics = run_ast_checks(
            file_rule_input.path,
            file_rule_input.file_content,
            self.compile_args,
            checks=self.checks,
        )

        if not diagnostics:
            return ResultType(ResultTypeEnum.Ok)

        description = "\n".join(d.format() for d in diagnostics)
        return ResultType(ResultTypeEnum.Error, description)
