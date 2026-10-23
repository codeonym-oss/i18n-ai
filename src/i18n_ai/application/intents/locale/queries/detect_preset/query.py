from dataclasses import dataclass
from pathlib import Path

from mediary.cqrs import Query, query

from .view import PresetMatch


@query
@dataclass(frozen=True)
class DetectPresetQuery(Query[PresetMatch | None]):
    """The preset of the project at `root`, from its manifests and config files, or the one
    `name`d, with where its locales are; None when no library is revealed. Raises
    `PresetUnknown` for a name no preset has."""

    root: Path
    name: str | None = None
