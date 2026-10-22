import logging
from importlib.metadata import version
from typing import Annotated

import typer
from rich.logging import RichHandler

from ..di.messaging.mediator import LOGGER as MEDIATOR_LOGGER
from .common.runner import errors
from .handlers.scan import scan

app = typer.Typer(
    name="i18n-ai",
    help=(
        "Generate a website's locales from its source locale tree, with LLM agents that keep "
        "placeholders intact."
    ),
    no_args_is_help=True,
    pretty_exceptions_show_locals=False,
)
app.command("scan")(scan)


def _version(value: bool) -> None:
    if value:
        typer.echo(f"i18n-ai {version('i18n-ai')}")
        raise typer.Exit()


@app.callback()
def root(
    verbose: Annotated[
        int,
        typer.Option("--verbose", "-v", count=True, help="-v for the steps, -vv for everything."),
    ] = 0,
    show_version: Annotated[
        bool, typer.Option("--version", callback=_version, is_eager=True, help="Show the version.")
    ] = False,
) -> None:
    level = logging.WARNING if verbose == 0 else logging.INFO if verbose == 1 else logging.DEBUG
    logging.basicConfig(
        level=level,
        format="%(message)s",
        handlers=[RichHandler(console=errors, show_path=verbose > 1, rich_tracebacks=True)],
    )
    if verbose == 0:
        # A refusal is shown as one line by the runner; its traceback is for -v
        MEDIATOR_LOGGER.setLevel(logging.CRITICAL)
    if verbose < 2:
        # The HTTP clients' request lines drown the steps
        for noisy in ("httpx", "httpcore", "openai", "anthropic"):
            logging.getLogger(noisy).setLevel(logging.WARNING)


def main() -> None:
    app()
