from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path

from ....domain.exports.locale import LocaleCode, LocaleTree


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


class ILocaleTreeScanner(ABC):
    """Finds a locale tree and reads its source files."""

    @abstractmethod
    async def scan(self, request: TreeRequest) -> LocaleTree:
        """Raises `LocaleTreeNotFound`, or `SourceLocaleUnknown` when several locales could be
        the source."""
        raise NotImplementedError
