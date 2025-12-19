"""Module initializing logger for mstd checks."""

import logging
import os

__DEBUG_DEVOPS_CHECKS__ = os.getenv("DEBUG_DEVOPS_CHECKS", "0")
__DEBUG_DEVOPS_UTILS__ = os.getenv("DEBUG_DEVOPS_UTILS", "0")

# TODO(97gamjak): centralize env logic if needed elsewhere
# https://github.com/97gamjak/mstd/issues/26
if int(__DEBUG_DEVOPS_CHECKS__) > 0:
    logging.basicConfig(level=logging.DEBUG)
else:
    logging.basicConfig(level=logging.INFO)

cpp_check_logger = logging.getLogger("devops_cpp_checks")
utils_logger = logging.getLogger("devops_utils")
config_logger = logging.getLogger("devops_config")

if int(__DEBUG_DEVOPS_UTILS__) > 0:
    utils_logger.setLevel(logging.DEBUG)
else:
    utils_logger.setLevel(logging.INFO)
