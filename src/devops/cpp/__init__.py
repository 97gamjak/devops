"""Package defining C++ check rules."""

from .buggy_cpp_files import filter_buggy_cpp
from .build_rules import build_cpp_rules
from .checks import run_cpp_checks
from .license_header import add_license_header

__all__ = [
    "add_license_header",
    "build_cpp_rules",
    "filter_buggy_cpp",
    "run_cpp_checks",
]

# `devops.cpp.ast` (AST-based checks, e.g. ASTChecksRule/Check/registry) is
# intentionally not imported here: it requires the optional 'libclang'
# dependency, and `build_cpp_rules` already imports it lazily behind a
# try/except. Import `devops.cpp.ast` directly if you need it.
