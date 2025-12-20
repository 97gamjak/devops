"""Git configuration parsing module."""

from __future__ import annotations

from dataclasses import dataclass

from .base import get_bool, get_str, get_table


@dataclass
class GitConfig:
    """Dataclass to hold default git configuration values."""

    tag_prefix: str = ""
    empty_tag_list_allowed: bool = True

    def to_toml_lines(self) -> list[str]:
        """Convert the GitConfig to TOML lines.

        Returns
        -------
        list[str]
            The list of TOML lines representing the configuration.

        """
        lines = ["[git]\n"]
        lines.append(f'#tag_prefix = "{self.tag_prefix}"\n')
        lines.append(
            f"#empty_tag_list_allowed = {str(self.empty_tag_list_allowed).lower()}\n"
        )
        return lines


def parse_git_config(raw_config: dict) -> GitConfig:
    """Parse git configuration from a raw dictionary.

    Parameters
    ----------
    raw_config: dict
        The raw git configuration dictionary.

    Returns
    -------
    GitConfig
        The parsed GitConfig dataclass instance.
    """
    table = get_table(raw_config, "git")

    tag_prefix = get_str(table, "tag_prefix", GitConfig.tag_prefix)

    empty_tag_list_allowed = get_bool(
        table, "empty_tag_list_allowed", default=GitConfig.empty_tag_list_allowed
    )

    return GitConfig(
        tag_prefix=tag_prefix,
        empty_tag_list_allowed=empty_tag_list_allowed,
    )
