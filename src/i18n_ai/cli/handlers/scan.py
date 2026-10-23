from pathlib import Path
from typing import Annotated

import typer

from ...application.exports.locale import ScanLocaleTreeQuery
from ...application.ports.locale import TreeRequest
from ...di import Bootstrap
from ...domain.exports.locale import LocaleFormat, LocaleTreeNotFound
from ..common import PresetOption, locales, project_tree, run, tree_request, with_preset
from ..rendering import render_scan


def scan(
    path: Annotated[
        Path | None,
        typer.Argument(
            help=(
                "A locale directory (locales/en), file (en.json), bundle, or the directory "
                "holding the locales. Default: where the project's preset keeps them."
            ),
            show_default=False,
        ),
    ] = None,
    targets: Annotated[
        list[str] | None,
        typer.Option(
            "--target", "-t", help="A locale to plan for; repeat, or separate with commas."
        ),
    ] = None,
    source: Annotated[
        str | None,
        typer.Option("--source", "-s", help="The source locale, when the tree has several."),
    ] = None,
    output: Annotated[
        Path | None,
        typer.Option(
            "--output", "-o", help="Where the target locales go; beside the source by default."
        ),
    ] = None,
    include: Annotated[
        list[str] | None,
        typer.Option("--include", help="Only the source files matching this glob."),
    ] = None,
    exclude: Annotated[
        list[str] | None,
        typer.Option("--exclude", help="Leave out the source files matching this glob."),
    ] = None,
    format: Annotated[
        LocaleFormat | None,
        typer.Option(
            "--format",
            "-f",
            help="Read only the locale files in this format, when the tree mixes several.",
            case_sensitive=False,
        ),
    ] = None,
    preset: PresetOption = None,
) -> None:
    """Scan a locale tree: its layout, its source files, and what each target needs. With no
    path, the tree is where the project's i18n library keeps its locales."""
    tree = tree_request(path or Path(), source, output, include, exclude, format)
    codes = locales(targets)

    async def flow(app: Bootstrap) -> int:
        request: TreeRequest | None = tree
        if path is None:
            request = await project_tree(app.mediator, app.console, tree, preset)
        else:
            request, _ = await with_preset(app.mediator, app.console, tree, preset, given=True)
        if request is None:
            raise LocaleTreeNotFound(
                str(Path.cwd()),
                "it has no preset's locales and no single locale tree; name the tree's path",
            )
        report = await app.mediator.send(ScanLocaleTreeQuery(request, codes))
        render_scan(app.console, report)
        return 0 if report.qualified else 1

    run(flow)
