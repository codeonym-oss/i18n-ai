from dataclasses import dataclass

from .....ports.locale import MessageRef, RecordedFallback


@dataclass(frozen=True)
class FallbackView:
    """A recorded fallback. `ref` is the message it is, `source` the text it is translated from
    and `current` the target's text now; `ref` and `source` are None when the entry is stale:
    its source file, its locale or its message is no longer in the tree."""

    entry: RecordedFallback
    ref: MessageRef | None
    source: str | None
    current: str | None

    @property
    def stale(self) -> bool:
        return self.ref is None


@dataclass(frozen=True)
class FallbacksView:
    """The record's fallbacks, in its order."""

    entries: tuple[FallbackView, ...]
