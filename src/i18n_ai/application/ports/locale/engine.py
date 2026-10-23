from abc import ABC, abstractmethod
from collections.abc import AsyncIterator, Mapping
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Any

from ....domain.exports.locale import (
    LocaleCode,
    LocaleDocument,
    MessageSyntax,
    SourceFile,
    Violation,
)
from ....domain.exports.provider import ResolvedModel


@dataclass(frozen=True)
class EngineSettings:
    """How the agents work.

    - `batch_size`: the messages sent in one call to the model.
    - `concurrency`: the calls to the model at once, across every file and locale.
    - `max_attempts`: how often a message is translated before it falls back to its source.
    - `classify`: whether the model confirms that each file is a locale document.
    - `context`: what the website is, to set the tone and the vocabulary."""

    model: ResolvedModel
    batch_size: int = 40
    concurrency: int = 8
    max_attempts: int = 3
    classify: bool = True
    context: str | None = None
    temperature: float | None = None


@dataclass(frozen=True)
class TranslationJob:
    """One source file into one target locale; `existing` is the target's current document,
    whose good translations are kept."""

    file: SourceFile
    document: LocaleDocument
    target: LocaleCode
    existing: LocaleDocument | None


@dataclass(frozen=True)
class EngineRequest:
    """The source files to translate into each target. `existing` maps a file's name and a
    target's key to the target's current document; `syntax` is the tree's messages'."""

    source: LocaleCode
    files: tuple[SourceFile, ...]
    targets: tuple[LocaleCode, ...]
    existing: Mapping[tuple[PurePosixPath, str], LocaleDocument]
    settings: EngineSettings
    syntax: MessageSyntax = MessageSyntax.STANDARD


@dataclass(frozen=True)
class FileClassified:
    """A file was classified. `subject` says what part of the website its messages are for."""

    file: SourceFile
    qualifies: bool
    reason: str
    subject: str | None = None


@dataclass(frozen=True)
class FileTranslated:
    """A file was translated into a target. `failures` are the messages that kept failing the
    rules, which hold their source text in `content`."""

    job: TranslationJob
    content: dict[str, Any]
    translated: int
    reused: int
    failures: tuple[Violation, ...]
    warnings: tuple[Violation, ...]


@dataclass(frozen=True)
class FileFailed:
    """A file could not be translated into a target at all, as when the model is unreachable."""

    job: TranslationJob
    error: str


EngineEvent = FileClassified | FileTranslated | FileFailed


class ITranslationEngine(ABC):
    """The agents: they classify each file, then translate each qualifying file into each
    target in parallel, and check every message against the rules."""

    @abstractmethod
    def run(self, request: EngineRequest) -> AsyncIterator[EngineEvent]:
        """The events, as they happen: a `FileClassified` for each file, then a
        `FileTranslated` or a `FileFailed` for each qualifying file and target."""
        raise NotImplementedError
