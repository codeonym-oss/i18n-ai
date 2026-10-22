import asyncio
import logging
from collections.abc import Awaitable, Callable

import typer
from pydantic import ValidationError
from rich.console import Console

from ...application.contract import ApplicationException
from ...di import Bootstrap, InfraException
from ...domain.contract import DomainException
from ...runtime.settings import build_settings

logger = logging.getLogger(__name__)

console = Console(highlight=False)
errors = Console(stderr=True, highlight=False)

Flow = Callable[[Bootstrap], Awaitable[int | None]]


def run(flow: Flow) -> None:
    """Run a CLI command's flow inside the app, and turn what it raises into an exit code: 2 for
    a refusal, with its message, 130 when interrupted."""
    try:
        settings = build_settings()
    except ValidationError as error:
        errors.print(f"[red]error:[/] the I18N_AI_* settings are invalid:\n{error}")
        raise typer.Exit(2) from error

    async def main() -> int | None:
        async with Bootstrap(settings, console) as app:
            return await flow(app)

    try:
        code = asyncio.run(main())
    except (DomainException, ApplicationException, InfraException) as error:
        errors.print(f"[red]error:[/] {error.message}")
        raise typer.Exit(2) from error
    except KeyboardInterrupt:
        errors.print("[yellow]interrupted[/]")
        raise typer.Exit(130) from None
    raise typer.Exit(code or 0)
