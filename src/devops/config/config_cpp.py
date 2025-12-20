"""Module for parsing C++ configuration."""

from dataclasses import dataclass

from devops.logger import config_logger

from .base import get_bool, get_str, get_table


@dataclass
class CppConfig:
    """Dataclass to hold C++ configuration values."""

    # Enable or disable running C++ style checks (e.g., clang-format, clang-tidy).
    style_checks: bool = True
    # Enable or disable verification that source files contain the expected license header.
    license_header_check: bool = True
    # Path to the license header file whose contents should be enforced, or None to use
    # the tool's default behavior (for example, no custom license header content).
    license_header: str | None = None
    # If True, limit checks to files that are currently staged (e.g., in a pre-commit hook).
    check_only_staged_files: bool = False


def parse_cpp_config(raw_config: dict) -> CppConfig:
    """Parse C++ configuration from a raw dictionary.

    Parameters
    ----------
    raw_config: dict
        The raw C++ configuration dictionary.

    Returns
    -------
    CppConfig
        The parsed CppConfig dataclass instance.
    """
    table = get_table(raw_config, "cpp")

    style_checks = get_bool(table, "style_checks", default=CppConfig.style_checks)

    license_header_check = get_bool(
        table, "license_header_check", default=CppConfig.license_header_check
    )

    license_header = get_str(table, "license_header")

    check_only_staged_files = get_bool(
        table, "check_only_staged_files", default=CppConfig.check_only_staged_files
    )

    config = CppConfig(
        style_checks=style_checks,
        license_header_check=license_header_check,
        license_header=license_header,
        check_only_staged_files=check_only_staged_files,
    )

    config_logger.debug(f"Parsed C++ configuration: {config}")

    return config
