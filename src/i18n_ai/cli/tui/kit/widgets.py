from rich.markup import escape
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widget import Widget
from textual.widgets import Label, Static


class Card(Vertical):
    """A rounded panel, its title on its border."""

    def __init__(self, *children: Widget, title: str = "", id: str | None = None) -> None:
        super().__init__(*children, id=id, classes="card")
        self.border_title = title


class KpiTile(Vertical):
    """A figure in a card: what it counts, the figure, and a note under it; `tone` colours the
    figure (`warning` for one to look at)."""

    def __init__(self, label: str, value: str, note: str, tone: str = "", id: str | None = None):
        super().__init__(id=id, classes="card kpi")
        self._label, self._value, self._note, self._tone = label, value, note, tone

    def compose(self) -> ComposeResult:
        yield Label(self._label, classes="kpi-label")
        tone = f" -{self._tone}" if self._tone else ""
        yield Static(escape(self._value), classes=f"kpi-value{tone}")
        yield Static(escape(self._note), classes="kpi-note")


class Chip(Static):
    """A glyph and a word on a pill of the `tone`'s colour: primary, secondary, accent, warning or
    error."""

    def __init__(self, glyph: str, word: str, tone: str, id: str | None = None) -> None:
        super().__init__(f"{glyph} {word}", id=id, classes=f"chip -{tone}")
