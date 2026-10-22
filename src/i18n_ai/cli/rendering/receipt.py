from rich.console import Console
from rich.table import Table

from ...application.exports.locale import GenerationReceipt, ResultStatus
from .scan import shown

_STYLES = {
    ResultStatus.WRITTEN: "green",
    ResultStatus.PARTIAL: "yellow",
    ResultStatus.REFUSED: "red",
    ResultStatus.IGNORED: "dim",
    ResultStatus.FAILED: "red",
}
# The failures and warnings listed, per file; the rest are counted.
_LISTED = 8


def render_receipt(console: Console, receipt: GenerationReceipt) -> None:
    # 1. Each file and target
    table = Table(
        title=f"Generated with {receipt.model}", title_justify="left", header_style="bold"
    )
    table.add_column("File")
    table.add_column("Locale", style="cyan")
    table.add_column("Status")
    table.add_column("Translated", justify="right")
    table.add_column("Kept", justify="right")
    table.add_column("Path / reason")
    order = list(ResultStatus)
    for result in sorted(
        receipt.results, key=lambda r: (order.index(r.status), r.file, r.target or "")
    ):
        style = _STYLES[result.status]
        detail = (
            result.reason if result.status in (ResultStatus.IGNORED, ResultStatus.FAILED) else None
        )
        table.add_row(
            result.file,
            result.target or "-",
            f"[{style}]{result.status.value}[/]",
            str(result.translated) if result.target else "-",
            str(result.reused) if result.target else "-",
            detail or (shown(result.path) if result.path else ""),
        )
    console.print(table)

    # 2. What failed the rules, and the warnings
    for result in receipt.results:
        if result.failures:
            console.print(
                f"[red]✗[/] {result.file} → {result.target}: {len(result.failures)} message(s) "
                "kept their source text"
            )
            for violation in result.failures[:_LISTED]:
                console.print(f"    [dim]{violation.path}[/] {violation.message}")
            if len(result.failures) > _LISTED:
                console.print(f"    [dim]… and {len(result.failures) - _LISTED} more[/]")
        if result.warnings:
            console.print(
                f"[yellow]![/] {result.file} → {result.target}: {len(result.warnings)} warning(s)"
            )
            for violation in result.warnings[:_LISTED]:
                console.print(f"    [dim]{violation.path}[/] {violation.message}")
            if len(result.warnings) > _LISTED:
                console.print(f"    [dim]… and {len(result.warnings) - _LISTED} more[/]")

    # 3. The totals
    counts = receipt.count()
    parts = [
        f"[{_STYLES[status]}]{counts[status]} {status.value}[/]"
        for status in ResultStatus
        if counts[status]
    ]
    console.print("  ".join(parts) or "nothing to do")
