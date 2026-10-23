"""Locale trees on disk: finding them, reading their source files, and writing the targets
the way their source is written, in its format (see `formats`). See `tree_scanner` for how a
tree is recognized."""

from .locale_store import FileSystemLocaleStore
from .tree_scanner import FileSystemLocaleTreeScanner

__all__ = ["FileSystemLocaleStore", "FileSystemLocaleTreeScanner"]
