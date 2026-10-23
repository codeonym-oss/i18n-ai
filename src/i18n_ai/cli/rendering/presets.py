from rich.console import Console
from rich.table import Table

from ...application.exports.locale import PresetMatch, PresetView
from .scan import shown


def render_presets(
    console: Console, presets: tuple[PresetView, ...], match: PresetMatch | None
) -> None:
    table = Table(title="Presets", title_justify="left", header_style="bold")
    table.add_column("Preset", style="cyan")
    table.add_column("Library")
    table.add_column("Detected from")
    table.add_column("Locales")
    table.add_column("Format")
    table.add_column("Placeholders")
    for preset in presets:
        here = match is not None and match.preset.name == preset.name
        table.add_row(
            f"{preset.name} [green]●[/]" if here else preset.name,
            preset.library,
            ", ".join(preset.detected_from),
            preset.example,
            preset.format or "[dim]any[/]",
            ", ".join(preset.placeholders),
        )
    console.print(table)
    if match is None:
        console.print("[dim]No i18n library is detected here.[/]")
    else:
        console.print(f"Here: {describe(match)}")


def describe(match: PresetMatch) -> str:
    """`Preset i18next · react-i18next in package.json → public/locales`"""
    preset = match.preset
    why = "--preset" if match.reason == "chosen" else match.reason
    line = f"Preset [cyan]{preset.name}[/] [dim]· {why}[/]"
    if match.tree is None:
        return f"{line} [yellow]· no locales at {preset.example}[/]"
    where = f" [dim](from {match.tree_from})[/]" if match.tree_from else ""
    return f"{line} → {shown(match.tree)}{where}"
