"""Locale trees on disk: finding them, reading their source files, and writing the targets
the way their source is written, in its format (see `formats`), and what a project reveals
of its i18n library (`project_inspector`). See `tree_scanner` for how a
tree is recognized."""

from .fallback_record import FileSystemFallbackRecord
from .locale_store import FileSystemLocaleStore
from .project_inspector import FileSystemProjectInspector
from .tree_scanner import FileSystemLocaleTreeScanner

__all__ = [
    "FileSystemFallbackRecord",
    "FileSystemLocaleStore",
    "FileSystemLocaleTreeScanner",
    "FileSystemProjectInspector",
]
