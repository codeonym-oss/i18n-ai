from collections.abc import Callable
from dataclasses import dataclass

from textual import on
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.content import Content
from textual.fuzzy import Matcher
from textual.screen import ModalScreen
from textual.style import Style
from textual.widgets import Input, OptionList, Static
from textual.widgets.option_list import Option

# A prefix: the group it keeps; the groups show in this order
PREFIXES = {">": "Commands", "@": "Go to", "#": "Files"}
TITLE_WIDTH = 28
HINT_WIDTH = 30


@dataclass(frozen=True)
class PaletteEntry:
    """A result of the palette: its group (one of `PREFIXES`' values), its glyph, its title, a
    hint, its key, and what choosing it does."""

    group: str
    glyph: str
    title: str
    hint: str
    key: str
    run: Callable[[], object]


class PaletteScreen(ModalScreen[PaletteEntry | None]):
    """A search over the commands, the tree's locales and its files: `>`, `@` or `#` first keeps
    one group, the rest of the text is matched against the titles; the results by group, best
    first. Enter closes it with the highlighted entry, escape with none."""

    BINDINGS = [
        Binding("escape", "close", "Close", show=False),
        Binding("down", "move(1)", show=False, priority=True),
        Binding("up", "move(-1)", show=False, priority=True),
    ]

    def __init__(self, entries: list[PaletteEntry]) -> None:
        super().__init__()
        self._entries = entries
        self._shown: list[PaletteEntry] = []

    def compose(self) -> ComposeResult:
        with Vertical(id="palette-box"):
            yield Input(
                placeholder="Search · > commands  @ locales  # files",
                id="palette-input",
                compact=True,
            )
            yield OptionList(id="palette-results", compact=True)
            yield Static("↑↓ move · ⏎ run · esc close", id="palette-keys")

    def on_mount(self) -> None:
        self._show("")

    @on(Input.Changed, "#palette-input")
    def _typed(self, event: Input.Changed) -> None:
        self._show(event.value)

    def _show(self, text: str) -> None:
        """The entries `text` keeps, by group, a header before each."""
        group = PREFIXES.get(text[:1])
        words = (text[1:] if group else text).strip()
        matcher = Matcher(words, match_style=Style(bold=True, underline=True))
        options: list[Option] = []
        self._shown = []
        for name in PREFIXES.values():
            if group not in (None, name):
                continue
            scored = [
                (matcher.match(entry.title) if words else 1.0, index, entry)
                for index, entry in enumerate(self._entries)
                if entry.group == name
            ]
            hits = sorted((s for s in scored if s[0] > 0), key=lambda s: (-s[0], s[1]))
            if not hits:
                continue
            options.append(Option(Content.styled(name.upper(), "bold $text-muted"), disabled=True))
            for _, _, entry in hits:
                options.append(Option(_line(entry, matcher, bool(words)), id=str(len(self._shown))))
                self._shown.append(entry)
        results = self.query_one("#palette-results", OptionList)
        results.set_options(options or [Option("nothing matches", disabled=True)])
        first = next((i for i, option in enumerate(options) if not option.disabled), None)
        results.highlighted = first

    def action_move(self, by: int) -> None:
        results = self.query_one("#palette-results", OptionList)
        if by > 0:
            results.action_cursor_down()
        else:
            results.action_cursor_up()

    @on(Input.Submitted, "#palette-input")
    def _submitted(self) -> None:
        results = self.query_one("#palette-results", OptionList)
        if results.highlighted is not None:
            self._choose(results.get_option_at_index(results.highlighted).id)

    @on(OptionList.OptionSelected, "#palette-results")
    def _selected(self, event: OptionList.OptionSelected) -> None:
        self._choose(event.option.id)

    def _choose(self, id: str | None) -> None:
        if id is not None:
            self.dismiss(self._shown[int(id)])

    def action_close(self) -> None:
        self.dismiss(None)


def _line(entry: PaletteEntry, matcher: Matcher, lit: bool) -> Content:
    """A result: its glyph, its title (the matched letters lit), its hint and its key."""
    title = matcher.highlight(entry.title) if lit else Content(entry.title)
    return Content.assemble(
        Content.styled(f"{entry.glyph} ", "$primary"),
        title.truncate(TITLE_WIDTH, ellipsis=True, pad=True),
        "  ",
        Content.styled(entry.hint[:HINT_WIDTH].ljust(HINT_WIDTH), "$text-muted"),
        "  ",
        Content.styled(entry.key, "bold $secondary"),
    )
