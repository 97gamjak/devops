"""Top level package for devops."""

from pathlib import Path

from devops.config import init_config

__NOT_DEFINED__ = object()
__GLOBAL_CONFIG__ = __NOT_DEFINED__

__BASE_DIR__ = Path(__file__).resolve().parent


if __GLOBAL_CONFIG__ is __NOT_DEFINED__:
    __GLOBAL_CONFIG__ = init_config()
