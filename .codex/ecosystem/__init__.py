"""Portable, local coordination over the shared independent-review gate."""

from .core import Engine, Error, default_state_dir, discover_active

__all__ = ["Engine", "Error", "default_state_dir", "discover_active"]
