"""Module for parsing C++ configuration."""

from dataclasses import dataclass

from devops.logger import config_logger

from .base import get_bool, get_str, get_table


@dataclass
class CppConfig:
    """Dataclass to hold C++ configuration values."""

    # Enable or disable running C++ style checks (e.g., clang-format, clang-tidy).
    style_checks: bool = True

    # Enable or disable verification that source files contain
    # the expected license header.
    license_header_check: bool = True

    # Path to the license header file whose contents should be enforced, or None to use
    # the tool's default behavior (for example, no custom license header content).
    license_header: str | None = None

    # If True, limit checks to files that are currently staged
    # (e.g., in a pre-commit hook).
    check_only_staged_files: bool = False

    # If True, enforce that header guards match the file path.
    # This helps ensure consistency and prevents duplicate header guards.
    header_guards_according_to_filepath: bool = False

    def to_toml_lines(self) -> list[str]:
        """Convert the CppConfig to TOML lines.

        Returns
        -------
        list[str]
            The list of TOML lines representing the configuration.

        """
        lines = ["[cpp]\n"]

        lines.append(f"#style_checks = {str(self.style_checks).lower()}\n")
        lines.append(
            f"#license_header_check = {str(self.license_header_check).lower()}\n"
        )

        if self.license_header is None:
            license_header = "<some file path>"
        else:
            license_header = f'"{self.license_header}"'

        lines.append(f"#license_header = {license_header}\n")

        lines.append(
            f"#check_only_staged_files = {str(self.check_only_staged_files).lower()}\n"
        )

        lines.append(
            "#header_guards_according_to_filepath = "
            f"{str(self.header_guards_according_to_filepath).lower()}\n"
        )

        return lines


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

    header_guards_according_to_filepath = get_bool(
        table,
        "header_guards_according_to_filepath",
        default=CppConfig.header_guards_according_to_filepath,
    )

    config = CppConfig(
        style_checks=style_checks,
        license_header_check=license_header_check,
        license_header=license_header,
        check_only_staged_files=check_only_staged_files,
        header_guards_according_to_filepath=header_guards_according_to_filepath,
    )

    config_logger.debug(f"Parsed C++ configuration: {config}")

    return config
