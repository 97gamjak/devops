"""Module for Git-related constants and functions."""

from .tag import GitTagError, get_latest_tag

__all__ = ["GitTagError", "get_latest_tag"]
