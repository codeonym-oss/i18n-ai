from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from ...application.exports.locale import ScanReport

_LAYOUTS = {
    "directory": "one directory per locale",
    "file": "one file per locale",
    "bundle": "every locale in one file",
}


def shown(path: Path) -> str:
    """`path` relative to the working directory when it is under it."""
    try:
        return str(path.relative_to(Path.cwd()))
    except ValueError:
        return str(path)


def render_scan(console: Console, report: ScanReport, overwrite: bool = False) -> None:
    # 1. The tree
    summary = Table.grid(padding=(0, 2))
    summary.add_column(style="bold")
    summary.add_column()
    summary.add_row("Layout", f"{report.layout} [dim]({_LAYOUTS.get(report.layout, '')})[/]")
    left_alone = ", ".join(report.left_alone)
    summary.add_row(
        "Format",
        f"{report.format} [yellow](the preset's; the {left_alone} files are left alone, "
        "--format chooses)[/]"
        if left_alone
        else report.format,
    )
    where = (
        f"(the keys of {', '.join(report.source_from)})"
        if report.source_from
        else shown(report.source_path)
    )
    summary.add_row("Source", f"[cyan]{report.source}[/] {report.source_name} [dim]{where}[/]")
    summary.add_row("Output", shown(report.output))
    summary.add_row("Existing", ", ".join(report.existing) or "[dim]none[/]")
    console.print(Panel(summary, title="Locale tree", title_align="left", border_style="blue"))

    # 2. The source files
    files = Table(title="Source files", title_justify="left", header_style="bold")
    files.add_column("File")
    files.add_column("Messages", justify="right")
    files.add_column("Qualifies")
    for file in report.files:
        mark = "[green]✓[/]" if file.qualifies else "[red]✗[/]"
        files.add_row(
            file.name, str(file.messages) if file.qualifies else "-", f"{mark} {file.reason}"
        )
    console.print(files)

    # 3. The targets
    if not report.targets:
        return
    targets = Table(title="Targets", title_justify="left", header_style="bold")
    targets.add_column("Locale", style="cyan")
    targets.add_column("File")
    targets.add_column("Writes to")
    targets.add_column("State")
    targets.add_column("To translate", justify="right")
    for target in report.targets:
        label = (
            f"{target.locale}\n[dim]{target.name}{' · rtl' if target.direction == 'rtl' else ''}[/]"
        )
        for index, planned in enumerate(target.files):
            where = shown(planned.path) + (
                f" [dim]→ {planned.bundle_key}[/]" if planned.bundle_key else ""
            )
            if not planned.exists:
                state, count = "[green]new[/]", planned.to_translate
            elif overwrite:
                state, count = "[yellow]overwrite[/]", planned.to_translate + planned.reusable
            else:
                state, count = f"fill [dim]({planned.reusable} kept)[/]", planned.to_translate
            targets.add_row(label if index == 0 else "", planned.file, where, state, str(count))
        if target.files:
            targets.add_section()
    console.print(targets)
