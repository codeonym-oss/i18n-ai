from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from .....domain.exports.locale import KeyPath, LocaleFormat, SourceFile


class FileFormat(ABC):
    """How one format's locale files are read and written. A new format is a new adapter, added
    to `FORMATS`, and a member of `LocaleFormat`."""

    format: LocaleFormat
    extensions: tuple[str, ...]  # lowercase, with the dot: `.yml`
    label: str  # as an error names it: `JSON`

    @abstractmethod
    def read(self, path: Path, source: bool = False) -> Any:
        """The content of `path`, as plain dicts, lists, strings and numbers, its keys strings:
        as a source's when `source`, for a format whose files hold both a source text and a
        translation. Raises `OSError`, or `ValueError` when it is not valid."""
        raise NotImplementedError

    def notes(self, path: Path) -> dict[KeyPath, str]:
        """What `path` says about its messages for their translators, by their path."""
        return {}

    @abstractmethod
    def write(
        self,
        path: Path,
        content: dict[str, Any],
        like: SourceFile,
        key: str | None,
        locale: str | None = None,
    ) -> None:
        """Write `content` to `path` as `like` is written. Under `key` when given: in the file
        already at `path`, keeping its other keys, else in a new one. `locale` is the target's,
        for a format that names it in the file."""
        raise NotImplementedError
