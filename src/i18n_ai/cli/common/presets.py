import dataclasses
from pathlib import Path

from mediary import Mediator
from rich.console import Console

from ...application.exports.locale import DetectLocaleTreesQuery, DetectPresetQuery, PresetMatch
from ...application.ports.locale import TreeRequest
from ...domain.exports.locale import LocaleFormat, MessageSyntax
from ..rendering import describe, shown


async def with_preset(
    mediator: Mediator, console: Console, request: TreeRequest, named: str | None, given: bool
) -> tuple[TreeRequest, PresetMatch | None]:
    """The request with the project's preset applied, and the preset, said: its locales'
    directory, unless a path is `given`; and, for its own locales or when it is `named`, its
    format, read alone when the tree mixes it with others (which the scan then says), and its
    messages' syntax. The preset is the one `named`, else the one detected."""
    match = await mediator.send(DetectPresetQuery(Path.cwd(), named))
    if match is None:
        return request, None
    console.print(describe(match))
    if not given and match.tree is not None:
        request = dataclasses.replace(request, path=match.tree)
    if given and named is None and not _within(request.path, match.tree):
        return request, match
    if match.preset.format is not None:
        request = dataclasses.replace(request, preferred=LocaleFormat(match.preset.format))
    return dataclasses.replace(request, syntax=MessageSyntax(match.preset.syntax)), match


def _within(path: Path, tree: Path | None) -> bool:
    return tree is not None and path.resolve().is_relative_to(tree.resolve())


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
