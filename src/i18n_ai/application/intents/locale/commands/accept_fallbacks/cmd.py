from dataclasses import dataclass

from mediary.cqrs import Command, command

from .....ports.locale import RecordedFallback, TreeRequest


@command
@dataclass(frozen=True)
class AcceptFallbacksCommand(Command[None]):
    """Keep `entries` as they are, in their source text: they leave the record, and the next run
    does not translate them again. No locale file changes. Raises `LocaleTreeNotFound`,
    `SourceLocaleUnknown` or `MixedLocaleFormats`."""

    tree: TreeRequest
    entries: tuple[RecordedFallback, ...]
