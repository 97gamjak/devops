"""AST-based (libclang) C++ checks for devops.

Add a new check by subclassing `Check` in `devops.cpp.ast.checks`, then
registering an instance in `devops.cpp.ast.registry.ALL_CHECKS`. It will
automatically run in the same shared AST walk as every other check, with
no changes needed to `engine.py` or `rule.py`.

Requires the optional `libclang` dependency (``pip install devops[ast]``).
"""

from .base import Check, Diagnostic
from .registry import ALL_CHECKS
from .rule import ASTChecksRule

__all__ = ["ALL_CHECKS", "ASTChecksRule", "Check", "Diagnostic"]
