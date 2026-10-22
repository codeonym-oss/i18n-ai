from typing import Annotated

import typer

from ...application.exports.provider import (
    GetProviderStatusQuery,
    InstallProviderCommand,
    ListProvidersQuery,
)
from ...di import Bootstrap
from ...domain.exports.provider import ModelSpec
from ..common import run
from ..rendering import render_providers

providers = typer.Typer(
    help="The model providers, and their LangChain packages.", no_args_is_help=True
)


@providers.command("list")
def list_providers() -> None:
    """List the providers LangChain can use, and which are installed."""

    async def flow(app: Bootstrap) -> int:
        render_providers(app.console, await app.mediator.send(ListProvidersQuery()))
        return 0

    run(flow)


@providers.command("install")
def install_provider(
    provider: Annotated[
        str, typer.Argument(help="The provider, e.g. openai, anthropic, ollama, google_genai.")
    ],
) -> None:
    """Install a provider's LangChain package into i18n-ai's environment, unless it is there."""

    async def flow(app: Bootstrap) -> int:
        receipt = await app.mediator.send(InstallProviderCommand(provider))
        verb = "installed" if receipt.installed_now else "already installed"
        app.console.print(f"[green]✓[/] {receipt.package} {verb} for [cyan]{receipt.provider}[/]")
        return 0

    run(flow)


@providers.command("check")
def check_provider(
    model: Annotated[str, typer.Argument(help="The model, as provider:model.")],
) -> None:
    """Tell a model's provider and package, and whether it is installed."""

    async def flow(app: Bootstrap) -> int:
        status = await app.mediator.send(GetProviderStatusQuery(ModelSpec(model)))
        mark = "[green]installed[/]" if status.installed else "[yellow]not installed[/]"
        app.console.print(f"[cyan]{status.provider}[/] · {status.model} · {status.package} {mark}")
        return 0 if status.installed else 1

    run(flow)
