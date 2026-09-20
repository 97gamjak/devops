"""Module for parsing C++ configuration."""

from dataclasses import dataclass, field

from devops.logger import config_logger

from .base import get_bool, get_str, get_str_list, get_table


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

    # If non-empty, only these directories (relative to cwd) are scanned.
    # Overrides the default behaviour of scanning all top-level directories.
    # Ignored when check_only_staged_files is True.
    check_dirs: list[str] = field(default_factory=list)

    # Directory names to skip during recursive scanning.
    # Applied regardless of whether check_dirs is set.
    exclude_dirs: list[str] = field(default_factory=list)

    # If True, enforce that header guards match the file path.
    # This helps ensure consistency and prevents duplicate header guards.
    header_guards_according_to_filepath: bool = False

    # Enable or disable libclang AST-based checks (see devops.cpp.ast).
    # Requires the optional 'ast' extra (`pip install devops[ast]`).
    ast_checks: bool = True

    # Compiler flags passed to libclang when parsing files for AST checks
    # (e.g. C++ standard, include paths). Used as fallback when
    # ast_check_compile_commands_db is not set or a file is not in the database.
    ast_check_compile_args: list[str] = field(default_factory=lambda: ["-std=c++23"])

    # Path to the directory containing compile_commands.json (e.g. "build").
    # When set, per-file compile flags are read from the database instead of
    # ast_check_compile_args. Falls back to ast_check_compile_args for files
    # not listed in the database.
    ast_check_compile_commands_db: str | None = None

    # If non-empty, only AST checks whose id is in this list run (allowlist).
    # See devops.cpp.ast.registry.ALL_CHECKS for available ids.
    ast_check_enabled_ids: list[str] = field(default_factory=list)

    # AST checks whose id is in this list never run, regardless of
    # ast_check_enabled_ids. See devops.cpp.ast.registry.ALL_CHECKS.
    ast_check_disabled_ids: list[str] = field(default_factory=list)

    # Per-check configuration keyed by check id.  Each value is a free-form
    # dict whose keys/types are defined by the individual check's configure()
    # method.  Declared in TOML as sub-tables of cpp.ast_check_config.
    ast_check_config: dict[str, dict] = field(default_factory=dict)

    # Path to the JSON file used to persist incremental check state.
    # When set (non-None, non-empty), cpp_checks runs in incremental mode
    # automatically: only new, previously-failed, or modified files are
    # re-checked on each run.  The CLI --incremental flag can also enable
    # this; when both are set, --state-file takes precedence.
    incremental_state_file: str | None = None

    # When True (the default), cpp_checks stops at the first file that
    # fails and reports an error.  Set to False to check all files
    # regardless of failures — useful in incremental mode to get a full
    # picture of the codebase in a single pass.  Can also be disabled via
    # the CLI --no-fail-fast flag.
    fail_fast: bool = True

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

        check_dirs = ", ".join(f'"{d}"' for d in self.check_dirs)
        lines.append(f"#check_dirs = [{check_dirs}]\n")

        excl_dirs = ", ".join(f'"{d}"' for d in self.exclude_dirs)
        lines.append(f"#exclude_dirs = [{excl_dirs}]\n")

        lines.append(
            "#header_guards_according_to_filepath = "
            f"{str(self.header_guards_according_to_filepath).lower()}\n"
        )

        lines.append(f"#ast_checks = {str(self.ast_checks).lower()}\n")

        args = ", ".join(f'"{arg}"' for arg in self.ast_check_compile_args)
        lines.append(f"#ast_check_compile_args = [{args}]\n")

        db = (
            f'"{self.ast_check_compile_commands_db}"'
            if self.ast_check_compile_commands_db
            else '"build"'
        )
        lines.append(f"#ast_check_compile_commands_db = {db}\n")

        enabled = ", ".join(f'"{cid}"' for cid in self.ast_check_enabled_ids)
        lines.append(f"#ast_check_enabled_ids = [{enabled}]\n")

        disabled = ", ".join(f'"{cid}"' for cid in self.ast_check_disabled_ids)
        lines.append(f"#ast_check_disabled_ids = [{disabled}]\n")

        lines.append(
            "#\n"
            "# Per-check configuration (one sub-table per check id):\n"
            "#[cpp.ast_check_config.paramNameForType]\n"
            '#type_to_name = { SimulationBox = "simulationBox", '
            'ForceField = "forceField" }\n'
        )

        isf = (
            f'"{self.incremental_state_file}"'
            if self.incremental_state_file
            else '"build/.cpp_check_state.json"'
        )
        lines.append(f"#incremental_state_file = {isf}\n")

        lines.append(f"#fail_fast = {str(self.fail_fast).lower()}\n")

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

    check_dirs = get_str_list(table, "check_dirs")

    exclude_dirs = get_str_list(table, "exclude_dirs")

    header_guards_according_to_filepath = get_bool(
        table,
        "header_guards_according_to_filepath",
        default=CppConfig.header_guards_according_to_filepath,
    )

    ast_checks = get_bool(table, "ast_checks", default=CppConfig.ast_checks)

    ast_check_compile_args = get_str_list(
        table,
        "ast_check_compile_args",
        default=["-std=c++23"],
    )

    ast_check_compile_commands_db = get_str(table, "ast_check_compile_commands_db")

    ast_check_enabled_ids = get_str_list(table, "ast_check_enabled_ids")

    ast_check_disabled_ids = get_str_list(table, "ast_check_disabled_ids")

    raw_check_config = get_table(table, "ast_check_config")
    ast_check_config = {
        check_id: get_table(raw_check_config, check_id) for check_id in raw_check_config
    }

    incremental_state_file = get_str(table, "incremental_state_file") or None

    fail_fast = get_bool(table, "fail_fast", default=CppConfig.fail_fast)

    config = CppConfig(
        style_checks=style_checks,
        license_header_check=license_header_check,
        license_header=license_header,
        check_only_staged_files=check_only_staged_files,
        check_dirs=check_dirs,
        exclude_dirs=exclude_dirs,
        header_guards_according_to_filepath=header_guards_according_to_filepath,
        ast_checks=ast_checks,
        ast_check_compile_args=ast_check_compile_args,
        ast_check_compile_commands_db=ast_check_compile_commands_db,
        ast_check_enabled_ids=ast_check_enabled_ids,
        ast_check_disabled_ids=ast_check_disabled_ids,
        ast_check_config=ast_check_config,
        incremental_state_file=incremental_state_file,
        fail_fast=fail_fast,
    )

    config_logger.debug(f"Parsed C++ configuration: {config}")

    return config
