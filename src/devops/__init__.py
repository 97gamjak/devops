"""Top level package for devops."""

from pathlib import Path

from devops.config import GlobalConfig, read_config
from devops.logger import config_logger

__NOT_DEFINED__ = object()

__BASE_DIR__ = Path(__file__).resolve().parent
__TOML_FILE_NAMES__ = ["devops.toml", ".devops.toml"]

__GLOBAL_CONFIG__ = __NOT_DEFINED__


def is_config_initialized() -> bool:
    """Check if global config paths have been initialized.

    Returns
    -------
    bool
        True if initialized, False otherwise.
    """
    return __GLOBAL_CONFIG__ is not __NOT_DEFINED__


def init_config() -> GlobalConfig:
    """Initialize global config paths."""
    found_configs = [
        Path(fname) for fname in __TOML_FILE_NAMES__ if Path(fname).is_file()
    ]
    if len(found_configs) == 1:
        config = read_config(Path(found_configs[0]))
    elif len(found_configs) > 1:
        config_logger.warning(
            "Multiple config files found: %s. Using no config file.",
            ", ".join(str(p) for p in found_configs),
        )
        config = read_config()
    else:
        config_logger.debug("No config file found. Using default configuration.")
        config = read_config()

    return config


if not is_config_initialized():
    __GLOBAL_CONFIG__ = init_config()
