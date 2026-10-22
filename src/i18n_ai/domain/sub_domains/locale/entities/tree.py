from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from ..vo.layout import TreeLayout
from ..vo.locale_code import LocaleCode
from .document import LocaleDocument


@dataclass(frozen=True)
class SourceFile:
    """A file of the source locale. `name` is its path inside the source locale's directory
    (`auth/login.json`), or the file's own name for the other layouts. `document` is None
    when the file is not a JSON object, and `error` says why."""

    name: PurePosixPath
    path: Path
    document: LocaleDocument | None
    error: str | None = None


@dataclass(frozen=True)
class TargetLocation:
    """Where a target locale's version of a source file goes: a file, and in a bundle the key
    under which it goes."""

    path: Path
    bundle_key: str | None = None


@dataclass(frozen=True)
class LocaleTree:
    """A website's locales, as found on disk: how they are laid out, which one is the source,
    the source's files, and the other locales already there.

    `root` holds the locale directories, the locale files, or is the bundle file itself; the
    targets are written under `output`, which is `root` unless asked otherwise."""

    root: Path
    layout: TreeLayout
    source: LocaleCode
    files: tuple[SourceFile, ...]
    existing: tuple[LocaleCode, ...]
    output: Path

    @property
    def source_path(self) -> Path:
        if self.layout == TreeLayout.DIRECTORY:
            return self.root / self.source.value
        if self.layout == TreeLayout.FILE:
            return self.files[0].path if self.files else self.root / f"{self.source.value}.json"
        return self.root

    def target_location(self, target: LocaleCode, file: SourceFile) -> TargetLocation:
        """Where `target`'s version of `file` goes. A locale that already exists keeps its own
        spelling, so `pt_BR/` is filled though `pt-BR` was asked."""
        name = self._existing_spelling(target)
        if self.layout == TreeLayout.DIRECTORY:
            return TargetLocation(self.output / name / Path(file.name))
        if self.layout == TreeLayout.FILE:
            return TargetLocation(self.output / f"{name}{file.path.suffix or '.json'}")
        output = self.output if self.output.suffix else self.output / self.root.name
        return TargetLocation(output, bundle_key=name)

    def has(self, locale: LocaleCode) -> bool:
        return any(existing.same_as(locale) for existing in self.existing)

    def _existing_spelling(self, target: LocaleCode) -> str:
        for existing in self.existing:
            if existing.same_as(target):
                return existing.value
        return target.value
