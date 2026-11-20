"""Tests for devops.config.config_release."""

import pytest

from devops.config import ReleaseConfig
from devops.config.base import ConfigError
from devops.config.config import parse_config
from devops.config.config_release import parse_release_config


def test_defaults() -> None:
    """A missing [release] table gives the defaults."""
    config = parse_release_config({})
    assert config == ReleaseConfig()
    assert config.branch == "main"
    assert config.ci_workflows == []
    assert config.ci_timeout == 1800
    assert config.ci_interval == 20


def test_values_are_read() -> None:
    """All keys are read from the table."""
    config = parse_release_config(
        {
            "release": {
                "branch": "master",
                "ci_workflows": ["ci.yml", "lint.yml"],
                "ci_timeout": 60,
                "ci_interval": 5,
            }
        }
    )
    assert config == ReleaseConfig("master", ["ci.yml", "lint.yml"], 60, 5)


def test_global_config_has_release() -> None:
    """parse_config fills GlobalConfig.release."""
    config = parse_config({"release": {"ci_workflows": ["ci.yml"]}})
    assert config.release.ci_workflows == ["ci.yml"]


@pytest.mark.parametrize(
    ("table", "message"),
    [
        ({"ci_timeout": -1}, "ci_timeout"),
        ({"ci_interval": 0}, "ci_interval"),
        ({"ci_workflows": "ci.yml"}, "ci_workflows"),
        ({"branch": 1}, "branch"),
    ],
)
def test_invalid_values(table: dict, message: str) -> None:
    """Wrong types and out-of-range numbers are config errors."""
    with pytest.raises(ConfigError, match=message):
        parse_release_config({"release": table})


def test_toml_lines() -> None:
    """The template lists every key, commented out."""
    lines = ReleaseConfig(ci_workflows=["ci.yml"]).to_toml_lines()
    assert lines == [
        "[release]\n",
        '#branch = "main"\n',
        '#ci_workflows = ["ci.yml"]\n',
        "#ci_timeout = 1800\n",
        "#ci_interval = 20\n",
    ]
