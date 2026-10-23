from mediary.cqrs import QueryHandler, query_handler

from ......domain.exports.locale import PRESETS, Preset, preset_named
from .....ports.locale import IProjectInspector
from .query import DetectPresetQuery
from .view import PresetMatch, PresetView


@query_handler
class DetectPresetQueryHandler(QueryHandler[DetectPresetQuery, PresetMatch | None]):
    """The first preset the project reveals whose locales are found, else the first it reveals:
    a Nuxt app depends on vue-i18n too, and the table puts Nuxt first."""

    def __init__(self, inspector: IProjectInspector) -> None:
        self._inspector = inspector

    async def handle(self, query: DetectPresetQuery) -> PresetMatch | None:
        if query.name is not None:
            return await self._match(query, preset_named(query.name), "chosen")

        dependencies = await self._inspector.dependencies(query.root)
        revealed: list[PresetMatch] = []
        for preset in PRESETS:
            reason = next(
                (
                    f"{package} in {dependencies[package]}"
                    for package in preset.packages
                    if package in dependencies
                ),
                None,
            )
            for pattern in preset.files:
                if reason is None:
                    reason = await self._inspector.find(query.root, pattern)
            if reason is None:
                continue
            match = await self._match(query, preset, reason)
            if match.tree is not None:
                return match
            revealed.append(match)
        return revealed[0] if revealed else None

    async def _match(self, query: DetectPresetQuery, preset: Preset, reason: str) -> PresetMatch:
        """Where the preset's locales are: what its config files say, else its usual places."""
        for hint in preset.config:
            configured = await self._inspector.configured(query.root, hint)
            if configured is not None:
                return PresetMatch(view(preset), reason, configured[0], configured[1])
        for tree in preset.trees:
            if await self._inspector.is_directory(query.root / tree):
                return PresetMatch(view(preset), reason, query.root / tree, None)
        return PresetMatch(view(preset), reason, None, None)


def view(preset: Preset) -> PresetView:
    return PresetView(
        name=preset.name,
        library=preset.library,
        example=preset.example,
        detected_from=(*preset.packages, *preset.files),
        format=preset.format.value if preset.format is not None else None,
        placeholders=tuple(style.value for style in preset.placeholders),
    )
