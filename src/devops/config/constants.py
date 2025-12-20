"""Constants for DevOps checks."""


class GitConstants:
    """Class holding constant Git-related URLs."""

    github_url: str = "https://github.com"
    github_devops_repo: str = github_url + "/97gamjak/devops"
    github_devops_issues_url: str = github_devops_repo + "/issues"
    github_default_owner_url: str = github_url + "/repo/owner"


GITHUB_CONSTANTS: GitConstants = GitConstants()


class Constants:
    """Class holding constant values for DevOps checks."""

    github: GitConstants = GITHUB_CONSTANTS
