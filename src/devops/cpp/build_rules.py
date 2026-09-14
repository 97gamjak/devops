"""Module to build C++ rules based on global configuration."""

from devops import __GLOBAL_CONFIG__
from devops.config import CppConfig
from devops.logger import cpp_check_logger
from devops.rules import Rule

from .license_header import CheckLicenseHeader
from .style_rules import cpp_style_rules

try:
    from .ast import ASTChecksRule
except ImportError:
    ASTChecksRule = None


def build_cpp_rules(config: CppConfig = __GLOBAL_CONFIG__.cpp) -> list[Rule]:
    """Build and return the list of C++ rules based on the global configuration.

    Parameters
    ----------
    config: CppConfig
        The global C++ configuration.

    Returns
    -------
    list[Rule]
        The list of C++ rules.

    """
    rules = []

    if config.style_checks:
        rules += cpp_style_rules

    if config.ast_checks:
        if ASTChecksRule is not None:
            rules.append(
                ASTChecksRule(
                    compile_args=config.ast_check_compile_args,
                    compile_commands_db=config.ast_check_compile_commands_db,
                    enabled_check_ids=config.ast_check_enabled_ids,
                    disabled_check_ids=config.ast_check_disabled_ids,
                    check_config=config.ast_check_config,
                )
            )
        else:
            cpp_check_logger.warning(
                "AST-based C++ checks are enabled, but 'libclang' is not "
                "installed. Install the 'ast' extra "
                "(`pip install devops[ast]`) to enable them. "
                "Skipping AST checks."
            )

    if config.license_header_check:
        if config.license_header is not None:
            rules.append(CheckLicenseHeader(config.license_header))
        else:
            cpp_check_logger.warning(
                "License header check is enabled, "
                "but no license header text is provided in the configuration."
                "This rule will be skipped."
            )

    return rules
