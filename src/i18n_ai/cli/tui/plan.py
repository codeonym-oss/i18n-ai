from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import Footer, Header, Static

from ...application.exports.locale import ScanReport, TargetFileView
from ...domain.exports.locale import LocaleCode
from ..common.setup import Planned, planned
from .grid import JobGrid


class PlanScreen(Screen[Planned | None]):
    """What a run will do, file by file and locale by locale, before it starts: each cell new,
    fill or up to date with its messages to translate, or turned off. A cell, a row or a column
    turns off; Run gives the targets, the files left out and the cells skipped."""

    DEFAULT_CSS = """
    PlanScreen #grid { height: auto; max-height: 1fr; }
    PlanScreen #left-out { color: $text-muted; padding: 1 1 0 1; }
    PlanScreen #total { padding: 1 1 0 1; }
    """
    BINDINGS = [
        Binding("space", "cell", "Cell"),
        Binding("r", "row", "Row"),
        Binding("c", "column", "Column"),
        Binding("ctrl+r", "run", "Run"),
        Binding("b,escape", "back", "Back"),
    ]

    def __init__(self, report: ScanReport) -> None:
        super().__init__()
        self._files = [file.name for file in report.qualified]
        self._targets = [target.locale for target in report.targets]
        self._cells: dict[tuple[str, str], TargetFileView] = {
            (file.file, target.locale): file for target in report.targets for file in target.files
        }
        self._left_out = [file for file in report.files if not file.qualifies]
        self._off: set[tuple[str, str]] = set()

    def compose(self) -> ComposeResult:
        yield Header()
        yield JobGrid(self._files, self._targets, self._label, id="grid")
        yield Static(
            "\n".join(f"Left out: {file.name} — {file.reason}" for file in self._left_out),
            id="left-out",
        )
        yield Static("", id="total")
        yield Footer()

    def on_mount(self) -> None:
        self.query_one("#left-out").display = bool(self._left_out)
        self._total()

    def _label(self, file: str, locale: str) -> str:
        if (file, locale) in self._off:
            return "off"
        cell = self._cells[(file, locale)]
        if not cell.to_translate:
            return "up to date"
        return f"{'fill' if cell.exists else 'new'} {cell.to_translate}"

    def _total(self) -> None:
        on = [cell for pair, cell in self._cells.items() if pair not in self._off]
        messages = sum(cell.to_translate for cell in on)
        self.query_one("#total", Static).update(
            f"{count(len(on), 'agent')} · {count(messages, 'message')}"
        )

    def _toggle(self, pairs: list[tuple[str, str]]) -> None:
        """All of `pairs` off, or all on again when they are all off already."""
        if all(pair in self._off for pair in pairs):
            self._off.difference_update(pairs)
        else:
            self._off.update(pairs)
        grid = self.query_one(JobGrid)
        for file, locale in pairs:
            grid.show(file, locale, self._label(file, locale))
        self._total()

    def action_cell(self) -> None:
        cursor = self.query_one(JobGrid).under_cursor()
        if cursor is not None and cursor[1]:
            self._toggle([cursor])

    def action_row(self) -> None:
        cursor = self.query_one(JobGrid).under_cursor()
        if cursor is not None:
            self._toggle([(cursor[0], locale) for locale in self._targets])

    def action_column(self) -> None:
        cursor = self.query_one(JobGrid).under_cursor()
        if cursor is not None and cursor[1]:
            self._toggle([(file, cursor[1]) for file in self._files])

    def action_run(self) -> None:
        if all(pair in self._off for pair in self._cells):
            self.notify("Every cell is off: nothing to run.", severity="warning")
            return
        targets = [LocaleCode(locale) for locale in self._targets]
        self.dismiss(planned(self._files, targets, self._off))

    def action_back(self) -> None:
        self.dismiss(None)


def count(number: int, noun: str) -> str:
    return f"{number} {noun}" if number == 1 else f"{number} {noun}s"
