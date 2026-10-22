from rich.console import Console
from rich.table import Table

from ...application.exports.provider import ProviderView


def render_providers(console: Console, providers: tuple[ProviderView, ...]) -> None:
    table = Table(title="LangChain providers", title_justify="left", header_style="bold")
    table.add_column("Provider", style="cyan")
    table.add_column("Package")
    table.add_column("Installed")
    for provider in providers:
        table.add_row(
            provider.name, provider.package, "[green]✓[/]" if provider.installed else "[dim]-[/]"
        )
    console.print(table)
    console.print(
        "[dim]Use a model as provider:model, e.g. openai:gpt-4.1-mini or ollama:qwen2.5:14b[/]"
    )
