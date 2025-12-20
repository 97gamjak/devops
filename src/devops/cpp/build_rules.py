"""Module to build C++ rules based on global configuration."""

from devops import __GLOBAL_CONFIG__
from devops.config import CppConfig
from devops.logger import cpp_check_logger
from devops.rules import Rule

from .license_header import CheckLicenseHeader
from .style_rules import cpp_style_rules


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
