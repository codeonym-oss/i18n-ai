from dataclasses import dataclass
from pathlib import Path

from mediary.cqrs import Query, query

from .view import TreeCandidateView


@query
@dataclass(frozen=True)
class DetectLocaleTreesQuery(Query[tuple[TreeCandidateView, ...]]):
    """The locale trees under a project's directory, the shallowest first."""

    root: Path
