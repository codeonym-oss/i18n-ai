from datetime import UTC, datetime

from rich.console import Console
from rich.table import Table

from ...application.exports.provider import KeysView, ModelsView, ProviderView

# Where a key comes from, as the tables and messages say it.
SOURCES = {"env": "environment", ".env": ".env", "keyring": "keyring", "run": "this run"}


def render_providers(console: Console, providers: tuple[ProviderView, ...]) -> None:
    table = Table(title="LangChain providers", title_justify="left", header_style="bold")
    table.add_column("Provider", style="cyan")
    table.add_column("Package")
    table.add_column("Installed")
    table.add_column("API key")
    for provider in providers:
        key = "[dim]-[/]"
        if provider.key:
            key = f"[dim]{provider.key}[/]"
            if provider.key_source:
                key = f"[green]✓[/] {provider.key} [dim]({SOURCES[provider.key_source]})[/]"
        table.add_row(
            provider.name,
            provider.package,
            "[green]✓[/]" if provider.installed else "[dim]-[/]",
            key,
        )
    console.print(table)
    console.print(
        "[dim]Use a model as provider:model, e.g. openai:gpt-4.1-mini or ollama:qwen2.5:14b[/]"
    )


def render_models(console: Console, models: ModelsView) -> None:
    table = Table(title=f"{models.provider} models", title_justify="left", header_style="bold")
    table.add_column("Model", style="cyan")
    table.add_column("Created")
    table.add_column("")
    for model in models.models:
        created = (
            datetime.fromtimestamp(model.created, UTC).date().isoformat() if model.created else ""
        )
        table.add_row(model.id, created, "[green]recommended[/]" if model.recommended else "")
    console.print(table)
    console.print(f"[dim]Use one as {models.provider}:<model> with --model, or I18N_AI_MODEL[/]")


def render_keys(console: Console, keys: KeysView) -> None:
    if keys.keyring:
        console.print(f"System keyring: [cyan]{keys.keyring}[/]")
    else:
        console.print(
            "[yellow]No system keyring here: keep the keys in the environment or a .env.[/]"
        )
    table = Table(title="API keys", title_justify="left", header_style="bold")
    table.add_column("Provider", style="cyan")
    table.add_column("Variable")
    table.add_column("From")
    for key in keys.keys:
        source = f"[green]✓[/] {SOURCES[key.source]}" if key.source else "[dim]-[/]"
        table.add_row(key.provider, key.variable, source)
    console.print(table)
    console.print(
        "[dim]Save a key with `i18n-ai auth login <provider>`; the environment and the .env "
        "win over the keyring.[/]"
    )
