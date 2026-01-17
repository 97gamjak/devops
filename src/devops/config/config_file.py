"""Module to parse file configuration values."""

from dataclasses import dataclass, field
from pathlib import Path

from .base import ConfigError, get_str, get_str_or_str_list, get_table


@dataclass(frozen=True)
class FileConfig:
    """Dataclass to hold file configuration values."""

    encoding: str = "utf-8"
    changelog_paths: list[Path] = field(default_factory=lambda: [Path("CHANGELOG.md")])
    _default_changelog_path: Path | None = None

    @property
    def default_changelog_path(self) -> Path:
        """Get the default changelog path.

        Returns
        -------
        Path
            The default changelog path.
        """
        if self._default_changelog_path is not None:
            return self._default_changelog_path

        return self.changelog_paths[0]

    def to_toml_lines(self) -> list[str]:
        """Convert the FileConfig to TOML lines.

        Returns
        -------
        list[str]
            The list of TOML lines representing the configuration.

        """
        lines = ["[file]\n"]
        lines.append(f'#encoding = "{self.encoding}"\n')
        paths_str = '", "'.join(str(p) for p in self.changelog_paths)
        lines.append(f'#changelog_paths = ["{paths_str}"]\n')
        lines.append(f'#default_changelog_path = "{self.default_changelog_path}"\n')
        return lines


def parse_file_config(raw_config: dict) -> FileConfig:
    """Parse file configuration from a raw dictionary.

    Parameters
    ----------
    raw_config: dict
        The raw file configuration dictionary.

    Returns
    -------
    FileConfig
        The parsed FileConfig dataclass instance.

    Raises
    ------
    ConfigError
        If the specified encoding is invalid.
    """
    table = get_table(raw_config, "file")

    encoding = parse_encoding(table)
    changelog_paths = parse_changelog_path(table)
    default_changelog_path = parse_default_changelog_path(table)

    return FileConfig(
        encoding=encoding,
        changelog_paths=changelog_paths,
        _default_changelog_path=default_changelog_path,
    )


def parse_encoding(table: dict) -> str:
    """Parse the encoding from a configuration table.

    Parameters
    ----------
    table: dict
        The configuration table.

    Returns
    -------
    str
        The parsed encoding.

    Raises
    ------
    ConfigError
        If the specified encoding is invalid.
    """
    encoding = get_str(table, "encoding", default=FileConfig.encoding)

    # Validate encoding
    try:
        Path(__file__).open("r", encoding=encoding).close()
    except LookupError as e:
        msg = f"Invalid file encoding specified in configuration: {encoding}"
        raise ConfigError(msg) from e

    return encoding


def parse_changelog_path(table: dict) -> list[Path]:
    """Parse the changelog paths from a configuration table.

    Parameters
    ----------
    table: dict
        The configuration table.

    Returns
    -------
    list[Path]
        The parsed list of changelog paths.
    """
    changelog_paths = get_str_or_str_list(
        table, "changelog_path", FileConfig.changelog_paths
    )

    if isinstance(changelog_paths, str):
        changelog_paths = [changelog_paths]

    return [Path(p) for p in changelog_paths]


def parse_default_changelog_path(table: dict) -> Path | None:
    """Parse the default changelog path from a configuration table.

    Parameters
    ----------
    table: dict
        The configuration table.

    Returns
    -------
    Path | None
        The parsed default changelog path, or None if not specified.
    """
    default_path_str = get_str(table, "default_changelog_path", default=None)

    if default_path_str is not None:
        return Path(default_path_str)

    return None
