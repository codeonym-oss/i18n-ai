from rich.markup import escape
from textual.app import ComposeResult, RenderResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.message import Message
from textual.widget import Widget
from textual.widgets import Label, Static

from .heat import strip


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


class LocaleCard(Vertical, can_focus=True):
    """A target locale to pick: its code, its direction, its name, and what a run would do
    with it; Space, Enter or a click toggles it."""

    BINDINGS = [Binding("space,enter", "pick", "Pick")]

    class Toggled(Message):
        def __init__(self, card: "LocaleCard") -> None:
            super().__init__()
            self.card = card

    def __init__(
        self, code: str, name: str, direction: str, state: str, in_tree: bool, picked: bool
    ) -> None:
        super().__init__(classes="locale-card")
        self.code, self.locale_name, self.state = code, name, state
        self.direction = direction.upper()
        self.in_tree, self.picked = in_tree, picked
        self.set_class(picked, "-picked")

    def compose(self) -> ComposeResult:
        with Horizontal(classes="locale-head"):
            yield Static(f"[b]{escape(self.code)}[/b]", classes="locale-code")
            yield Static(self.direction, classes="locale-direction")
            yield Static(self._check(), classes="locale-check")
        yield Static(escape(self.locale_name), classes="locale-name")
        tone = "-tree" if self.in_tree else "-new"
        yield Static(escape(self.state), classes=f"locale-state {tone}")

    def _check(self) -> str:
        return "■" if self.picked else "□"

    def action_pick(self) -> None:
        self.picked = not self.picked
        self.set_class(self.picked, "-picked")
        self.query_one(".locale-check", Static).update(self._check())
        self.post_message(self.Toggled(self))

    def on_click(self) -> None:
        self.focus()
        self.action_pick()


class PlanCell(Vertical, can_focus=True):
    """A file in a locale, in the plan: its state's tag, whether it is on, the messages it will
    translate, and the strip of its file's messages. The arrows post `Moved`."""

    BINDINGS = [
        Binding("up", "move(0, -1)", show=False),
        Binding("down", "move(0, 1)", show=False),
        Binding("left", "move(-1, 0)", show=False),
        Binding("right", "move(1, 0)", show=False),
    ]
    # A state: its words, and what the cell shows for its number
    WORDS = {"new": "new", "fill": "fill", "done": "up to date", "off": "off"}
    NUMBERS = {"done": "✓", "off": "—"}

    class Moved(Message):
        def __init__(self, cell: "PlanCell", columns: int, rows: int) -> None:
            super().__init__()
            self.cell, self.columns, self.rows = cell, columns, rows

    def __init__(self, file: str, locale: str) -> None:
        super().__init__(classes="plan-cell")
        self.file, self.locale = file, locale
        self.text = ""

    def compose(self) -> ComposeResult:
        with Horizontal(classes="cell-head"):
            yield Static(classes="cell-tag")
            yield Static(classes="cell-short")
            yield Static(classes="cell-mark")
        yield Static(classes="cell-number")
        yield _Strip()

    def show(self, state: str, to_translate: int, fallbacks: int, kept: int) -> None:
        """`state` is new, fill, done (up to date) or off; `text` says it as the plan reads."""
        for name in self.WORDS:
            self.set_class(name == state, f"-{name}")
        number = self.NUMBERS.get(state, str(to_translate))
        self.text = self.WORDS[state] + ("" if state in self.NUMBERS else f" {to_translate}")
        self.query_one(".cell-tag", Static).update(self.WORDS[state].upper())
        self.query_one(".cell-short", Static).update(number)
        self.query_one(".cell-mark", Static).update("□" if state == "off" else "■")
        self.query_one(".cell-number", Static).update(number)
        self.query_one(_Strip).counts = (to_translate, fallbacks, kept, state == "off")
        self.query_one(_Strip).refresh()

    def action_move(self, columns: int, rows: int) -> None:
        self.post_message(self.Moved(self, columns, rows))


class _Strip(Widget):
    """A cell's strip, drawn at its width."""

    def __init__(self) -> None:
        super().__init__(classes="cell-strip")
        self.counts = (0, 0, 0, False)

    def render(self) -> RenderResult:
        to_translate, fallbacks, kept, off = self.counts
        return strip(self.size.width, to_translate, fallbacks, kept, off)


class ModelCard(Static):
    """The run's model: its provider, the model, and its key's state."""

    def __init__(self, id: str | None = None) -> None:
        super().__init__(id=id, classes="model-card")
        self.text = ""
        self.show(None, None, "", False, False)

    def show(
        self,
        provider: str | None,
        model: str | None,
        key: str,
        needs_key: bool,
        recommended: bool,
    ) -> None:
        """`key` says the key's state; `needs_key` when one is still to be given."""
        if provider is None:
            self.text = "no model yet"
            self.update(f"[$text-muted]○ {self.text}[/]")
            return
        picked = escape(model) if model else "[$text-muted]pick a model[/]"
        self.text = f"{provider} / {model or '…'}" + (f" · {key}" if key else "")
        tone = "$warning" if needs_key or not model else "$success"
        star = "  [$accent]★ recommended[/]" if recommended else ""
        line = f"[{tone}]●[/] [b]{escape(provider)}[/b] / {picked}{star}"
        self.update(f"{line}\n[$text-muted]{escape(key)}[/]" if key else line)
