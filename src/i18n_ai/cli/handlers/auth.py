import sys
from typing import Annotated

import typer

from ...application.exports.provider import (
    KeysView,
    KeyView,
    ListProviderKeysQuery,
    ListProvidersQuery,
    RemoveProviderKeyCommand,
    SetProviderKeyCommand,
)
from ...di import Bootstrap
from ...domain.exports.provider import ProviderTakesNoKey, ProviderUnknown
from .. import interactive
from ..common import MissingParameter, run
from ..common.runner import errors
from ..rendering import SOURCES, render_keys

auth = typer.Typer(
    help="The providers' API keys, kept in the system keyring instead of a .env.",
    no_args_is_help=True,
)

Provider = Annotated[
    str | None,
    typer.Argument(
        help="The provider, e.g. openai, anthropic, google_genai. Asked for when missing.",
        show_default=False,
    ),
]

_NO_KEYRING = (
    "[red]error:[/] no system keyring is available here; keep the key in the environment or "
    "in a .env instead"
)


@auth.command("login")
def login(provider: Provider = None) -> None:
    """Save a provider's API key in the system keyring, for every project. The key is asked
    for, hidden, or read from stdin: `printenv OPENAI_API_KEY | i18n-ai auth login openai`."""
    asking = interactive.is_interactive(no_input=False)
    if provider is None and not asking:
        raise MissingParameter("argument", "'PROVIDER'")

    async def flow(app: Bootstrap) -> int:
        keys = await app.mediator.send(ListProviderKeysQuery())
        if keys.keyring is None:
            errors.print(_NO_KEYRING)
            return 2
        if provider is None:
            key = await _pick(keys.keys, "Which provider's key to save?")
        else:
            key = await _key_of(app, keys, provider)
        if asking:
            value = await interactive.prompter().secret(f"{key.variable} (hidden)")
        else:
            value = sys.stdin.readline().strip()
        if not value:
            errors.print(f"[red]error:[/] no {key.variable} given; nothing saved")
            return 2

        receipt = await app.mediator.send(SetProviderKeyCommand(key.provider, value, save=True))
        if not receipt.saved:
            errors.print(f"[red]error:[/] {receipt.problem}")
            return 2
        app.console.print(
            f"[green]✓[/] {receipt.variable} saved in the system keyring ({keys.keyring}) for "
            f"[cyan]{receipt.provider}[/]"
        )
        if receipt.source in ("env", ".env"):
            app.console.print(
                f"[yellow]{receipt.variable} is also set in the {SOURCES[receipt.source]}, "
                "which wins over the keyring.[/]"
            )
        return 0

    run(flow)


@auth.command("logout")
def logout(
    provider: Provider = None,
    every: Annotated[
        bool, typer.Option("--all", help="Remove every provider's key from the system keyring.")
    ] = False,
) -> None:
    """Remove a provider's API key from the system keyring."""
    asking = interactive.is_interactive(no_input=False)
    if provider is None and not every and not asking:
        raise MissingParameter("argument", "'PROVIDER'")

    async def flow(app: Bootstrap) -> int:
        keys = await app.mediator.send(ListProviderKeysQuery())
        if keys.keyring is None:
            errors.print(_NO_KEYRING)
            return 2
        if every:
            chosen = list(keys.keys)
        elif provider is not None:
            chosen = [await _key_of(app, keys, provider)]
        else:
            saved = [key for key in keys.keys if key.source == "keyring"]
            if not saved:
                app.console.print("No key is saved in the system keyring.")
                return 0
            chosen = [await _pick(saved, "Which provider's key to remove?")]

        removed = 0
        for key in chosen:
            removal = await app.mediator.send(RemoveProviderKeyCommand(key.provider))
            if removal.removed:
                removed += 1
                app.console.print(f"[green]✓[/] {removal.variable} removed from the system keyring")
            elif not every:
                app.console.print(f"No {removal.variable} in the system keyring.")
            if removal.source is not None and (removal.removed or not every):
                app.console.print(
                    f"[yellow]{removal.variable} is still set in the {SOURCES[removal.source]}.[/]"
                )
        if every and not removed:
            app.console.print("No key was saved in the system keyring.")
        return 0

    run(flow)


@auth.command("status")
def status() -> None:
    """Show which providers have an API key, and where it comes from: the environment, the
    project's .env, or the system keyring. Never the keys themselves."""

    async def flow(app: Bootstrap) -> int:
        render_keys(app.console, await app.mediator.send(ListProviderKeysQuery()))
        return 0

    run(flow)


async def _key_of(app: Bootstrap, keys: KeysView, provider: str) -> KeyView:
    name = provider.replace("-", "_").lower()
    for key in keys.keys:
        if key.provider == name:
            return key
    providers = [view.name for view in await app.mediator.send(ListProvidersQuery())]
    if name in providers:
        raise ProviderTakesNoKey(name)
    raise ProviderUnknown(provider, providers)


async def _pick(keys: tuple[KeyView, ...] | list[KeyView], question: str) -> KeyView:
    choices = [
        interactive.Choice(
            key.provider,
            f"{key.provider}  ({key.variable}"
            + (f" · {SOURCES[key.source]})" if key.source else ")"),
        )
        for key in keys
    ]
    name = await interactive.prompter().select(question, choices)
    return next(key for key in keys if key.provider == name)
