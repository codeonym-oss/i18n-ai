from collections.abc import Sequence

from rich.markup import escape
from textual import events, on
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Grid, Horizontal, ScrollableContainer, Vertical
from textual.content import Content
from textual.widget import Widget
from textual.widgets import Button, Static

from ...application.exports.locale import FallbackView, ScanReport, TargetFileView
from ...domain.exports.locale import LocaleCode
from ..common.setup import Planned, planned, within
from .kit.heat import legend
from .kit.shell import WIDE, ShellScreen
from .kit.widgets import Card, PlanCell

CELL_WIDTH = 18  # columns a cell takes at the least, past which the grid scrolls
SHOWN_OFF = 2  # cells off the status line names


class PlanScreen(ShellScreen[Planned | None]):
    """What a run will do, file by file and locale by locale, before it starts: each cell new,
    fill or up to date with its messages to translate, or turned off, and the inspector on the
    cell with the focus. A cell, a row or a column turns off; Run gives the targets, the files
    left out and the cells skipped."""

    DEFAULT_CSS = """
    PlanScreen #plan { height: 1fr; }
    PlanScreen #plan-main { width: 1fr; height: 1fr; }
    PlanScreen #plan-head { height: 1; }
    PlanScreen #nothing-sent { width: 1fr; text-align: right; color: $text-muted; padding: 0 2; }
    PlanScreen #run { min-width: 0; }
    PlanScreen #grid-top { height: auto; }
    PlanScreen .grid-corner { width: 24; color: $text-muted; text-style: bold; padding: 1 0 0 0; }
    PlanScreen #locale-strip { height: auto; overflow: hidden hidden; padding-right: 1; }
    PlanScreen #grid-body { height: 1fr; }
    PlanScreen #file-column { width: 24; overflow: hidden hidden; }
    PlanScreen #cells { scrollbar-gutter: stable; scrollbar-size-vertical: 1; }
    PlanScreen .columns { height: auto; grid-gutter: 0 1; }
    PlanScreen .column-head { height: 3; padding: 0 1; }
    PlanScreen .column-head-name { width: 1fr; text-wrap: nowrap; text-overflow: ellipsis; }
    PlanScreen .column-head-count { width: auto; color: $text-muted; }
    PlanScreen .file-head { height: 5; padding: 1 0 0 1; }
    PlanScreen .file-head-messages { color: $text-muted; }
    PlanScreen #legend { height: 1; margin-top: 1; }
    PlanScreen #legend-keys { width: auto; color: $text-muted; margin-right: 2; }
    PlanScreen .left-out {
        width: 1fr; color: $text-muted; text-align: right;
        text-wrap: nowrap; text-overflow: ellipsis;
    }
    PlanScreen #inspector { width: 44; margin-left: 1; }
    PlanScreen #run-bar { height: 3; margin-top: 1; padding: 0 1; }
    PlanScreen #run-label { width: auto; color: $text-muted; text-style: bold; margin-right: 2; }
    PlanScreen #total { width: 1fr; }
    PlanScreen #hints { width: auto; color: $text-muted; }
    PlanScreen.-narrow #plan { layout: vertical; }
    PlanScreen.-narrow #inspector { width: 1fr; max-height: 7; margin: 0; }
    PlanScreen.-narrow .column-head { height: 1; }
    PlanScreen.-narrow .file-head { height: 4; }
    PlanScreen.-narrow .grid-corner { padding: 0; }
    PlanScreen.-narrow #legend { margin: 0; }
    PlanScreen.-narrow #run-bar { height: 1; margin: 0; }
    PlanScreen.-narrow #hints { display: none; }
    """
    BINDINGS = [
        Binding("space", "cell", "Cell"),
        Binding("r", "row", "Row"),
        Binding("c", "column", "Column"),
        Binding("ctrl+r", "run", "Run"),
        Binding("b,escape", "back", "Back"),
    ]
    AUTO_FOCUS = "PlanCell"
    SECTION = "run"

    def __init__(
        self, report: ScanReport, fallbacks: Sequence[FallbackView] = (), batch: int = 40
    ) -> None:
        super().__init__()
        self._files = [file.name for file in report.qualified]
        self._messages = {file.name: file.messages for file in report.qualified}
        self._targets = [target.locale for target in report.targets]
        self._names = {target.locale: target.name for target in report.targets}
        self._source = report.source
        self._cells: dict[tuple[str, str], TargetFileView] = {
            (file.file, target.locale): file for target in report.targets for file in target.files
        }
        self._left_out = [file for file in report.files if not file.qualifies]
        self._fallbacks: dict[tuple[str, str], list[FallbackView]] = {}
        for entry in fallbacks:
            if entry.ref is not None:
                pair = (entry.ref.file.as_posix(), entry.ref.target.value)
                self._fallbacks.setdefault(pair, []).append(entry)
        self._batch = max(1, batch)
        self._off: set[tuple[str, str]] = set()
        self._inspected: tuple[str, str] | None = None

    def body(self) -> ComposeResult:
        with Horizontal(id="plan"):
            with Vertical(id="plan-main"):
                with Card(title="Plan", id="grid-card").add_class("-fill"):
                    with Horizontal(id="plan-head"):
                        yield Static("nothing sent to a model yet", id="nothing-sent")
                        yield Button("", id="run", variant="primary", compact=True)
                    # The locale headers and the file names keep in step with the cells' scroll
                    with Horizontal(id="grid-top"):
                        yield Static("FILE ╲ LOCALE", classes="grid-corner")
                        with ScrollableContainer(id="locale-strip", can_focus=False):
                            yield self._columns(self._locale_heads())
                    with Horizontal(id="grid-body"):
                        with ScrollableContainer(id="file-column", can_focus=False):
                            yield Vertical(*self._file_heads())
                        with ScrollableContainer(id="cells", can_focus=False):
                            cells = [
                                PlanCell(f, locale) for f in self._files for locale in self._targets
                            ]
                            yield self._columns(cells)
                    with Horizontal(id="legend"):
                        yield Static(legend(), id="legend-keys")
                        for file in self._left_out:
                            note = f"left out · {file.name} — {file.reason}"
                            yield Static(note, classes="left-out", markup=False)
                with Horizontal(id="run-bar"):
                    yield Static("THE RUN", id="run-label")
                    yield Static("", id="total")
                    yield Static("a cell [b]space[/b] · row [b]r[/b] · column [b]c[/b]", id="hints")
            with Card(title="Inspector", id="inspector").add_class("-accent"):
                yield Static("", id="inspected")

    def _locale_heads(self) -> list[Widget]:
        heads: list[Widget] = []
        for locale in self._targets:
            name = f"[b $primary]{escape(locale)}[/] [$text-muted]{escape(self._names[locale])}[/]"
            heads.append(
                Horizontal(
                    Static(name, classes="column-head-name"),
                    Static("", classes="column-head-count"),
                    classes="column-head",
                )
            )
        return heads

    def _file_heads(self) -> list[Widget]:
        return [
            Vertical(
                Static(f"[b]{escape(file)}[/b]"),
                Static(
                    f"{count(self._messages[file], 'message')} in {self._source}",
                    classes="file-head-messages",
                ),
                classes="file-head",
            )
            for file in self._files
        ]

    def _columns(self, widgets: Sequence[Widget]) -> Grid:
        """`widgets` a locale to a column, at `CELL_WIDTH` at the least, past which it scrolls."""
        grid = Grid(*widgets, classes="columns")
        grid.styles.grid_size_columns = max(1, len(self._targets))
        grid.styles.grid_columns = " ".join("1fr" for _ in self._targets) or "1fr"
        grid.styles.min_width = (CELL_WIDTH + 1) * len(self._targets)
        return grid

    def on_mount(self) -> None:
        crumb = Content.from_markup("[$text-muted]New run /[/] [b]Plan[/b]")
        self.query_one("#crumb", Static).update(crumb)
        for cell in self.query(PlanCell):
            self._show_cell(cell)
        self._total()
        self._inspect()
        cells = self.query_one("#cells")
        self.watch(cells, "scroll_x", self._scrolled_x)
        self.watch(cells, "scroll_y", self._scrolled_y)

    def _scrolled_x(self, x: float) -> None:
        self.query_one("#locale-strip").scroll_to(x=x, animate=False, force=True, immediate=True)

    def _scrolled_y(self, y: float) -> None:
        self.query_one("#file-column").scroll_to(y=y, animate=False, force=True, immediate=True)

    def status_tree(self) -> str:
        off = [
            f"{file} → {locale} off"
            for file in self._files
            for locale in self._targets
            if (file, locale) in self._off
        ]
        line = f"{len(self._cells) - len(off)} of {len(self._cells)} cells on"
        if off and not self.has_class("-narrow"):  # narrow, the keys need the room
            more = f" · +{len(off) - SHOWN_OFF} more" if len(off) > SHOWN_OFF else ""
            line += " · " + " · ".join(off[:SHOWN_OFF]) + more
        return f"{line}  ·  {super().status_tree()}"

    def _fit(self, width: int, height: int) -> None:
        super()._fit(width, height)
        # Beside the grid it takes the height; under it, its own
        self.query_one("#inspector").set_class(width >= WIDE, "-fill")
        self.query_one("#status-tree", Static).update(self.status_tree())

    def _state(self, file: str, locale: str) -> str:
        if (file, locale) in self._off:
            return "off"
        cell = self._cells[(file, locale)]
        if not cell.to_translate:
            return "done"
        return "fill" if cell.exists else "new"

    def _show_cell(self, cell: PlanCell) -> None:
        pair = (cell.file, cell.locale)
        target = self._cells[pair]
        fallbacks = len(self._fallbacks.get(pair, ()))
        cell.show(self._state(*pair), target.to_translate, fallbacks, target.reusable)

    def _total(self) -> None:
        on = [cell for _, cell in self._on()]
        messages = sum(cell.to_translate for cell in on)
        calls = sum(-(-cell.to_translate // self._batch) for cell in on)
        self.query_one("#total", Static).update(
            Content.from_markup(
                f"[b]{count(messages, 'message')}[/b] · [b]{count(len(on), 'agent')}[/b] · "
                f"[b]{count(calls, 'call')}[/b] of ≤{self._batch}"
            )
        )
        self.query_one("#run", Button).label = f"▶ Run {count(len(on), 'agent')} ⌃R"
        for locale, head in zip(
            self._targets, self.query(".column-head-count").results(Static), strict=True
        ):
            on_here = (cell for (_, there), cell in self._on() if there == locale)
            head.update(str(sum(cell.to_translate for cell in on_here)))
        self.query_one("#status-tree", Static).update(self.status_tree())

    def _on(self) -> list[tuple[tuple[str, str], TargetFileView]]:
        """The cells on, by file and locale."""
        return [(pair, cell) for pair, cell in self._cells.items() if pair not in self._off]

    def _inspect(self) -> None:
        """The inspector on the cell with the focus, or the first one."""
        pair = self._inspected or next(iter(self._cells), None)
        inspector = self.query_one("#inspector", Card)
        shown = self.query_one("#inspected", Static)
        if pair is None:
            inspector.border_title = "Inspector"
            shown.update("[$text-muted]no file to translate[/]")
            return
        file, locale = pair
        inspector.border_title = f"Inspector · {file} → {locale}"
        cell = self._cells[pair]
        state = PlanCell.WORDS[self._state(file, locale)]
        lines = [
            f"[b]{state}[/b] · {cell.to_translate} to translate · {cell.reusable} kept",
            f"[$text-muted]{escape(within(self.shell.project)(cell.path))}[/]",
            "",
        ]
        fallbacks = self._fallbacks.get(pair, [])
        if not fallbacks:
            lines.append("[$text-muted]no recorded fallback[/]")
        for entry in fallbacks:
            lines.append(f"[b]{escape(str(entry.entry.path))}[/b]  [b $warning]FALLBACK[/]")
            lines.append(f"[$text-muted]{escape(entry.source or '')}[/]")
        shown.update(Content.from_markup("\n".join(lines)))

    @on(events.DescendantFocus)
    def _focused(self, event: events.DescendantFocus) -> None:
        if isinstance(event.widget, PlanCell):
            self._inspected = (event.widget.file, event.widget.locale)
            self._inspect()

    @on(PlanCell.Moved)
    def _moved(self, event: PlanCell.Moved) -> None:
        row = self._files.index(event.cell.file) + event.rows
        column = self._targets.index(event.cell.locale) + event.columns
        if 0 <= row < len(self._files) and 0 <= column < len(self._targets):
            cell = self._cell(self._files[row], self._targets[column])
            cell.focus()
            cell.scroll_visible()

    @on(Button.Pressed, "#run")
    def _run_pressed(self) -> None:
        self.action_run()

    def _cell(self, file: str, locale: str) -> PlanCell:
        return next(c for c in self.query(PlanCell) if (c.file, c.locale) == (file, locale))

    def _focused_cell(self) -> PlanCell | None:
        return self.focused if isinstance(self.focused, PlanCell) else None

    def _toggle(self, pairs: list[tuple[str, str]]) -> None:
        """All of `pairs` off, or all on again when they are all off already."""
        if all(pair in self._off for pair in pairs):
            self._off.difference_update(pairs)
        else:
            self._off.update(pairs)
        for cell in self.query(PlanCell):
            if (cell.file, cell.locale) in pairs:
                self._show_cell(cell)
        self._total()
        self._inspect()

    def action_cell(self) -> None:
        cell = self._focused_cell()
        if cell is not None:
            self._toggle([(cell.file, cell.locale)])

    def action_row(self) -> None:
        cell = self._focused_cell()
        if cell is not None:
            self._toggle([(cell.file, locale) for locale in self._targets])

    def action_column(self) -> None:
        cell = self._focused_cell()
        if cell is not None:
            self._toggle([(file, cell.locale) for file in self._files])

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
