from dataclasses import dataclass

from mediary.cqrs import Query, query

from ..detect_preset import PresetView


@query
@dataclass(frozen=True)
class ListPresetsQuery(Query[tuple[PresetView, ...]]):
    """Every preset, in the order detection tries them."""
