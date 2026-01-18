"""Module to parse file configuration values."""

from dataclasses import dataclass
from pathlib import Path

from .base import ConfigError, get_str, get_table


@dataclass(frozen=True)
class FileConfig:
    """Dataclass to hold file configuration values."""

    encoding: str = "utf-8"

    def to_toml_lines(self) -> list[str]:
        """Convert the FileConfig to TOML lines.

        Returns
        -------
        list[str]
            The list of TOML lines representing the configuration.

        """
        lines = ["[file]\n"]
        lines.append(f'#encoding = "{self.encoding}"\n')
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

    encoding = get_str(table, "encoding", default=FileConfig.encoding)

    try:
        Path(__file__).open("r", encoding=encoding).close()
    except LookupError as e:
        msg = f"Invalid file encoding specified in configuration: {encoding}"
        raise ConfigError(msg) from e

    return FileConfig(encoding=encoding)
