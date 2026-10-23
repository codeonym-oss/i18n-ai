import dataclasses
from pathlib import Path

from mediary import Mediator
from rich.console import Console

from ...application.exports.locale import DetectLocaleTreesQuery, DetectPresetQuery, PresetMatch
from ...application.ports.locale import TreeRequest
from ...domain.exports.locale import LocaleFormat
from ..rendering import describe, shown


async def with_preset(
    mediator: Mediator, console: Console, request: TreeRequest, named: str | None, given: bool
) -> tuple[TreeRequest, PresetMatch | None]:
    """The request with the project's preset applied, and the preset, said: its format, unless
    one is asked, and its locales' directory, unless a path is `given`. The preset is the one
    `named`, else the one detected when no path is given."""
    if given and named is None:
        return request, None
    match = await mediator.send(DetectPresetQuery(Path.cwd(), named))
    if match is None:
        return request, None
    console.print(describe(match))
    if request.format is None and match.preset.format is not None:
        request = dataclasses.replace(request, format=LocaleFormat(match.preset.format))
    if not given and match.tree is not None:
        request = dataclasses.replace(request, path=match.tree)
    return request, match


async def project_tree(
    mediator: Mediator, console: Console, request: TreeRequest, named: str | None
) -> TreeRequest | None:
    """The request of a run given no path: with its preset's locales, else the project's only
    locale tree; None when there is neither."""
    request, match = await with_preset(mediator, console, request, named, given=False)
    if match is not None and match.tree is not None:
        return request
    candidates = await mediator.send(DetectLocaleTreesQuery(Path.cwd()))
    if len(candidates) != 1:
        return None
    console.print(f"[dim]Locale tree: {shown(candidates[0].path)}[/]")
    return dataclasses.replace(request, path=candidates[0].path)
