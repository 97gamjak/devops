"""Sphinx configuration for the devops documentation."""

from __future__ import annotations

import os
import sys
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as get_version

# -- Path setup --------------------------------------------------------------
# Allow Sphinx to find the package when it is not installed (e.g. local
# ``sphinx-build`` runs against a checkout without ``pip install -e .``).
sys.path.insert(0, os.path.abspath("../../src"))

# -- Project information ------------------------------------------------------

project = "devops"
copyright = "2026, Jakob Gamper"  # noqa: A001
author = "Jakob Gamper"

# The full version, including alpha/beta/rc tags, is pulled automatically
# from the installed package metadata (set by setuptools_scm from Git tags),
# so this file never needs to be touched when a new version is released.
try:
    release = get_version("devops")
except PackageNotFoundError:
    release = "0.0.0"
version = ".".join(release.split(".")[:2])

# -- General configuration ----------------------------------------------------

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
    "sphinx.ext.intersphinx",
    "myst_parser",
]

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

# devops re-exports many classes in package __init__ modules for convenience
# (e.g. CppConfig lives in both devops.config and devops.config.config_cpp),
# which makes autodoc's type-hint cross-references ambiguous. That's a
# harmless naming collision, not a doc error, so silence it specifically.
suppress_warnings = ["ref.python"]

source_suffix = {
    ".rst": "restructuredtext",
    ".md": "markdown",
}

# -- Autodoc / Autosummary -----------------------------------------------------

autosummary_generate = True
autodoc_default_options = {
    "members": True,
    "undoc-members": True,
    "show-inheritance": True,
}
autodoc_typehints = "description"
autodoc_member_order = "bysource"
# Mock the optional libclang C-extension so Sphinx can import the ast modules
# when building docs without the 'ast' extra installed.
autodoc_mock_imports = ["clang"]

# -- Napoleon (NumPy-style docstrings, matching the project's convention) -----

napoleon_google_docstring = False
napoleon_numpy_docstring = True
napoleon_use_param = True
napoleon_use_rtype = False

# -- Intersphinx ---------------------------------------------------------------

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
}

# -- HTML output ----------------------------------------------------------------

html_theme = "sphinx_rtd_theme"
html_static_path = ["_static"]
html_theme_options = {
    "navigation_depth": 4,
    "collapse_navigation": False,
}
