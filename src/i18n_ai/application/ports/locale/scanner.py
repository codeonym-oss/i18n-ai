from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path

from ....domain.exports.locale import LocaleCode, LocaleTree, TreeLayout


@dataclass(frozen=True)
class TreeRequest:
    """Where to find a locale tree: a locale directory (`locales/en`), a locale file
    (`messages/en.json`), a bundle, or the directory that holds the locales, with the source
    named when the tree cannot tell it. `include` and `exclude` are globs over the source's
    file names."""

    path: Path
    source: LocaleCode | None = None
    output: Path | None = None
    include: tuple[str, ...] = ()
    exclude: tuple[str, ...] = ()


@dataclass(frozen=True)
class TreeCandidate:
    """A locale tree found under a project: the path to give `scan` (the directory holding the
    locales, or the bundle), its layout, and its locales."""

    path: Path
    layout: TreeLayout
    locales: tuple[LocaleCode, ...]


class ILocaleTreeScanner(ABC):
    """Finds a locale tree and reads its source files."""

    @abstractmethod
    async def scan(self, request: TreeRequest) -> LocaleTree:
        """Raises `LocaleTreeNotFound`, or `SourceLocaleUnknown` when several locales could be
        the source."""
        raise NotImplementedError

    @abstractmethod
    async def detect(self, root: Path) -> list[TreeCandidate]:
        """The locale trees under `root`, the shallowest first."""
        raise NotImplementedError
