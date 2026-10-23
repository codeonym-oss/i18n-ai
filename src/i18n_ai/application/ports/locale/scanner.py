from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path

from ....domain.exports.locale import LocaleCode, LocaleFormat, LocaleTree, TreeLayout


@dataclass(frozen=True)
class TreeRequest:
    """Where to find a locale tree: a locale directory (`locales/en`), a locale file
    (`messages/en.json`), a bundle, or the directory that holds the locales, with the source
    named when the tree cannot tell it. `include` and `exclude` are globs over the source's
    file names. `format` reads only that format's files; otherwise a tree must keep to one,
    unless it mixes the `preferred` format with others: its files alone are then read, and the
    tree says which formats are left alone."""

    path: Path
    source: LocaleCode | None = None
    output: Path | None = None
    include: tuple[str, ...] = ()
    exclude: tuple[str, ...] = ()
    format: LocaleFormat | None = None
    preferred: LocaleFormat | None = None


@dataclass(frozen=True)
class TreeCandidate:
    """A locale tree found under a project: the path to give `scan` (the directory holding the
    locales, or the bundle), its layout, its locales, and the formats of their files."""

    path: Path
    layout: TreeLayout
    locales: tuple[LocaleCode, ...]
    formats: tuple[LocaleFormat, ...]


class ILocaleTreeScanner(ABC):
    """Finds a locale tree and reads its source files."""

    @abstractmethod
    async def scan(self, request: TreeRequest) -> LocaleTree:
        """Raises `LocaleTreeNotFound`, `SourceLocaleUnknown` when several locales could be the
        source, or `MixedLocaleFormats`."""
        raise NotImplementedError

    @abstractmethod
    async def detect(self, root: Path) -> list[TreeCandidate]:
        """The locale trees under `root`, the shallowest first."""
        raise NotImplementedError
