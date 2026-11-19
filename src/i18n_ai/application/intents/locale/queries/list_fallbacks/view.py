from dataclasses import dataclass

from ......domain.exports.locale import LocaleCode
from .....ports.locale import MessageRef, RecordedFallback


@dataclass(frozen=True)
class FallbackView:
    """A recorded fallback. `ref` is the message it is, `source` the text it is translated from
    and `current` the target's text now; `ref` and `source` are None when the entry is stale:
    its source file, its locale or its message is no longer in the tree. `elsewhere` is the same
    message in the tree's other target locales: each one's code and its text there, None when its
    file or the message is missing; none for a stale entry."""

    entry: RecordedFallback
    ref: MessageRef | None
    source: str | None
    current: str | None
    elsewhere: tuple[tuple[LocaleCode, str | None], ...] = ()

    @property
    def stale(self) -> bool:
        return self.ref is None


@dataclass(frozen=True)
class FallbacksView:
    """The record's fallbacks, in its order."""

    entries: tuple[FallbackView, ...]
