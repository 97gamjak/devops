"""Release configuration parsing module."""

from __future__ import annotations

from dataclasses import dataclass, field

from .base import ConfigError, get_int, get_str, get_str_list, get_table


@dataclass(frozen=True)
class ReleaseConfig:
    """Dataclass to hold release configuration values."""

    branch: str = "main"
    ci_workflows: list[str] = field(default_factory=list)
    ci_timeout: int = 1800
    ci_interval: int = 20

    def to_toml_lines(self) -> list[str]:
        """Convert the ReleaseConfig to TOML lines.

        Returns
        -------
        list[str]
            The list of TOML lines representing the configuration.

        """
        workflows = ", ".join(f'"{workflow}"' for workflow in self.ci_workflows)
        return [
            "[release]\n",
            f'#branch = "{self.branch}"\n',
            f"#ci_workflows = [{workflows}]\n",
            f"#ci_timeout = {self.ci_timeout}\n",
            f"#ci_interval = {self.ci_interval}\n",
        ]


def parse_release_config(raw_config: dict) -> ReleaseConfig:
    """Parse release configuration from a raw dictionary.

    Parameters
    ----------
    raw_config: dict
        The raw configuration dictionary.

    Returns
    -------
    ReleaseConfig
        The parsed ReleaseConfig dataclass instance.

    Raises
    ------
    ConfigError
        If a CI timeout is negative or a CI interval is not positive.

    """
    table = get_table(raw_config, "release")

    branch = get_str(table, "branch", default=ReleaseConfig.branch)
    ci_workflows = get_str_list(table, "ci_workflows")
    ci_timeout = get_int(table, "ci_timeout", default=ReleaseConfig.ci_timeout)
    ci_interval = get_int(table, "ci_interval", default=ReleaseConfig.ci_interval)

    if ci_timeout < 0:
        msg = f"release.ci_timeout must not be negative, got {ci_timeout}"
        raise ConfigError(msg)
    if ci_interval <= 0:
        msg = f"release.ci_interval must be positive, got {ci_interval}"
        raise ConfigError(msg)

    return ReleaseConfig(
        branch=branch,
        ci_workflows=ci_workflows,
        ci_timeout=ci_timeout,
        ci_interval=ci_interval,
    )
