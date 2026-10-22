from importlib.metadata import version
from typing import Annotated

import typer

app = typer.Typer(
    name="i18n-ai",
    help=(
        "Generate a website's locales from its source locale tree, with LLM agents that keep "
        "placeholders intact."
    ),
    no_args_is_help=True,
    pretty_exceptions_show_locals=False,
)


def _version(value: bool) -> None:
    if value:
        typer.echo(f"i18n-ai {version('i18n-ai')}")
        raise typer.Exit()


@app.callback()
def root(
    show_version: Annotated[
        bool, typer.Option("--version", callback=_version, is_eager=True, help="Show the version.")
    ] = False,
) -> None:
    pass


def main() -> None:
    app()
