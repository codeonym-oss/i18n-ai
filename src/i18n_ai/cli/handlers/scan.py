from pathlib import Path
from typing import Annotated

import typer

from ...application.exports.locale import ScanLocaleTreeQuery
from ...di import Bootstrap
from ..common import locales, run, tree_request
from ..rendering import render_scan


def scan(
    path: Annotated[
        Path,
        typer.Argument(
            help=(
                "A locale directory (locales/en), file (en.json), bundle, or the directory "
                "holding the locales."
            )
        ),
    ],
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
) -> None:
    """Scan a locale tree: its layout, its source files, and what each target needs."""
    tree = tree_request(path, source, output, include, exclude)
    codes = locales(targets)

    async def flow(app: Bootstrap) -> int:
        report = await app.mediator.send(ScanLocaleTreeQuery(tree, codes))
        render_scan(app.console, report)
        return 0 if report.qualified else 1

    run(flow)
