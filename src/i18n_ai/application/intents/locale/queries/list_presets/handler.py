from mediary.cqrs import QueryHandler, query_handler

from ......domain.exports.locale import PRESETS
from ..detect_preset import PresetView, view
from .query import ListPresetsQuery


@query_handler
class ListPresetsQueryHandler(QueryHandler[ListPresetsQuery, tuple[PresetView, ...]]):
    async def handle(self, query: ListPresetsQuery) -> tuple[PresetView, ...]:
        return tuple(view(preset) for preset in PRESETS)
