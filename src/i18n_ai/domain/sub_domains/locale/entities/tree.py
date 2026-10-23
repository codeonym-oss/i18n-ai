from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from ..vo.format import LocaleFormat
from ..vo.layout import TreeLayout
from ..vo.locale_code import LocaleCode
from .document import LocaleDocument


@dataclass(frozen=True)
class SourceFile:
    """A file of the source locale. `name` is its path inside the source locale's directory
    (`auth/login.json`), or the file's own name for the other layouts. `document` is None
    when the file is not an object, and `error` says why.

    `root_key` is the key the file holds its messages under: the source locale's in a bundle,
    and in a file whose only key is its locale, as Rails writes them (`en:`)."""

    name: PurePosixPath
    path: Path
    document: LocaleDocument | None
    error: str | None = None
    root_key: str | None = None


@dataclass(frozen=True)
class TargetLocation:
    """Where a target locale's version of a source file goes: a file, and the key under which
    it goes in a bundle or a file rooted at its locale. `locale` is the target as the tree
    spells it, for a format that names its locale inside the file (ARB's `@@locale`)."""

    path: Path
    bundle_key: str | None = None
    locale: str | None = None


@dataclass(frozen=True)
class LocaleTree:
    """A website's locales, as found on disk: how they are laid out, which one is the source,
    the source's files, and the other locales already there.

    `root` holds the locale directories, the locale files, or is the bundle file itself; the
    targets are written under `output`, which is `root` unless asked otherwise. Every source
    file is in one `format`."""

    root: Path
    layout: TreeLayout
    source: LocaleCode
    files: tuple[SourceFile, ...]
    existing: tuple[LocaleCode, ...]
    output: Path
    format: LocaleFormat = LocaleFormat.JSON
    prefix: str = ""

    @property
    def source_path(self) -> Path:
        if self.layout == TreeLayout.DIRECTORY:
            directory = self.root / self.source.value
            if self.files and not self.files[0].path.is_relative_to(directory):
                return self.files[0].path  # a template, as gettext's `messages.pot`
            return directory
        if self.layout == TreeLayout.FILE:
            return self.files[0].path if self.files else self.root / f"{self.prefix}{self.source}"
        return self.root

    def target_location(self, target: LocaleCode, file: SourceFile) -> TargetLocation:
        """Where `target`'s version of `file` goes. A locale that already exists keeps its own
        spelling, so `pt_BR/` is filled though `pt-BR` was asked; a new one is spelled as the
        format spells it."""
        name = self._existing_spelling(target)
        key = name if file.root_key is not None else None
        if self.layout == TreeLayout.DIRECTORY:
            return TargetLocation(self.output / name / Path(file.name), key, name)
        if self.layout == TreeLayout.FILE:
            suffix = self.format.target_suffix(file.path.suffix)
            path = self.output / f"{self.prefix}{name}{suffix}"
            return TargetLocation(path, key, name)
        output = self.output if self.output.suffix else self.output / self.root.name
        return TargetLocation(output, bundle_key=name, locale=name)

    def has(self, locale: LocaleCode) -> bool:
        return any(existing.same_as(locale) for existing in self.existing)

    def _existing_spelling(self, target: LocaleCode) -> str:
        for existing in self.existing:
            if existing.same_as(target):
                return existing.value
        return target.value.replace("-", self.format.locale_separator)
