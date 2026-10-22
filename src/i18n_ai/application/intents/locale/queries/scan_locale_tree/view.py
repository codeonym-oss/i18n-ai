from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class SourceFileView:
    """A source file, and whether it is a locale document worth translating."""

    name: str
    path: Path
    qualifies: bool
    reason: str
    messages: int


@dataclass(frozen=True)
class TargetFileView:
    """Where a target's version of a source file goes. `to_translate` messages need the model;
    `reusable` ones are already translated well in the existing file."""

    file: str
    path: Path
    bundle_key: str | None
    exists: bool
    to_translate: int
    reusable: int


@dataclass(frozen=True)
class TargetView:
    locale: str
    name: str
    direction: str
    exists: bool
    files: tuple[TargetFileView, ...]

    @property
    def to_translate(self) -> int:
        return sum(file.to_translate for file in self.files)


@dataclass(frozen=True)
class ScanReport:
    root: Path
    layout: str
    source: str
    source_name: str
    source_path: Path
    output: Path
    existing: tuple[str, ...]
    files: tuple[SourceFileView, ...]
    targets: tuple[TargetView, ...]

    @property
    def qualified(self) -> tuple[SourceFileView, ...]:
        return tuple(file for file in self.files if file.qualifies)

    @property
    def to_translate(self) -> int:
        return sum(target.to_translate for target in self.targets)
