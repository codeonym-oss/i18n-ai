"""Locale trees on disk: finding them, reading their source files, and writing the targets
in the source's JSON style. See `layout` for how a tree is recognized."""

from .locale_store import FileSystemLocaleStore
from .tree_scanner import FileSystemLocaleTreeScanner

__all__ = ["FileSystemLocaleStore", "FileSystemLocaleTreeScanner"]
