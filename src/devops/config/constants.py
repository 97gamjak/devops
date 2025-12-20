"""Constants for DevOps checks."""

from dataclasses import dataclass
from typing import ClassVar


@dataclass(frozen=True)
class GitConstants:
    """Class holding constant Git-related URLs."""

    github_url: str = "https://github.com"
    github_devops_repo: str = github_url + "/97gamjak/devops"
    github_devops_issues_url: str = github_devops_repo + "/issues"
    github_default_owner_url: str = github_url + "/repo/owner"


@dataclass(frozen=True)
class FileConstants:
    """Class holding constant file-related values."""

    toml_filenames: ClassVar[list[str]] = ["devops.toml", ".devops.toml"]


@dataclass(frozen=True)
class Constants:
    """Class holding constant values for DevOps checks."""

    github: GitConstants = GitConstants()
    files: FileConstants = FileConstants()
