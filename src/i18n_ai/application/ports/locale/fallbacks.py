from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from ....domain.exports.locale import KeyPath, ViolationCode


@dataclass(frozen=True)
class FallbackProblem:
    """A rule a fallback broke, as the record keeps it: the violation's code and message."""

    rule: ViolationCode
    message: str


@dataclass(frozen=True)
class RecordedFallback:
    """A message written in its source text because it kept failing the rules. `file` is the
    target file, relative to the record's directory, and `key` its locale's key in a bundle;
    `rejected` is the model's last translation, None when it gave none."""

    file: PurePosixPath
    key: str | None
    path: KeyPath
    problems: tuple[FallbackProblem, ...]
    rejected: str | None

    @property
    def target(self) -> tuple[PurePosixPath, str | None]:
        """The target it is in: its file and key."""
        return self.file, self.key


class IFallbackRecord(ABC):
    """The fallbacks the generations of a tree left, kept beside its targets, so the next run
    translates them again."""

    @abstractmethod
    async def read(self, directory: Path) -> tuple[RecordedFallback, ...]:
        """The record in `directory`; none when there is none, or it cannot be read."""
        raise NotImplementedError

    @abstractmethod
    async def write(self, directory: Path, entries: tuple[RecordedFallback, ...]) -> None:
        """Keep `entries` as the record in `directory`; without entries, there is no record."""
        raise NotImplementedError
