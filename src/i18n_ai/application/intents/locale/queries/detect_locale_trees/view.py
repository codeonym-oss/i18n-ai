from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class TreeCandidateView:
    """A locale tree found in a project, with the locale it would translate from: `en`, or the
    only one, or None when the user must choose."""

    path: Path
    layout: str
    locales: tuple[str, ...]
    source: str | None
    formats: tuple[str, ...] = ()
