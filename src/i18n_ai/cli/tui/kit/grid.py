from collections.abc import Mapping, Sequence

from rich.markup import escape
from textual import on
from textual.app import ComposeResult
from textual.containers import Grid, Horizontal, ScrollableContainer, Vertical
from textual.widget import Widget
from textual.widgets import Static

from .widgets import GridCell

CELL_WIDTH = 18  # columns a cell takes at the least, past which the grid scrolls


class CellGrid(Vertical):
    """Files × locales, a cell each: the locales' headers and the files' names stay in place while
    the cells scroll under them, and the arrows move the focus from cell to cell."""

    def __init__(
        self,
        files: Sequence[str],
        locales: Mapping[str, str],
        notes: Mapping[str, str],
        cells: Sequence[GridCell],
    ) -> None:
        """`locales` by code, with their names; `notes` a line under each file's name; `cells`
        a file to a row and a locale to a column, in that order."""
        super().__init__(id="grid")
        self._files = list(files)
        self._locales = dict(locales)
        self._notes = notes
        self._cells = list(cells)

    def compose(self) -> ComposeResult:
        with Horizontal(id="grid-top"):
            yield Static("FILE ╲ LOCALE", classes="grid-corner")
            with ScrollableContainer(id="locale-strip", can_focus=False):
                yield self._columns(self._heads())
        with Horizontal(id="grid-body"):
            with ScrollableContainer(id="file-column", can_focus=False):
                yield Vertical(*self._file_heads())
            with ScrollableContainer(id="cells", can_focus=False):
                yield self._columns(self._cells)

    def _heads(self) -> list[Widget]:
        return [
            Horizontal(
                Static(
                    f"[b $primary]{escape(code)}[/] [$text-muted]{escape(name)}[/]",
                    classes="column-head-name",
                ),
                Static("", classes="column-head-count"),
                classes="column-head",
            )
            for code, name in self._locales.items()
        ]

    def _file_heads(self) -> list[Widget]:
        return [
            Vertical(
                Static(f"[b]{escape(file)}[/b]"),
                Static(self._notes.get(file, ""), classes="file-head-note", markup=False),
                classes="file-head",
            )
            for file in self._files
        ]

    def _columns(self, widgets: Sequence[Widget]) -> Grid:
        """`widgets` a locale to a column, at `CELL_WIDTH` at the least, past which it scrolls."""
        grid = Grid(*widgets, classes="columns")
        grid.styles.grid_size_columns = max(1, len(self._locales))
        grid.styles.grid_columns = " ".join("1fr" for _ in self._locales) or "1fr"
        grid.styles.min_width = (CELL_WIDTH + 1) * len(self._locales)
        return grid

    def on_mount(self) -> None:
        cells = self.query_one("#cells")
        self.watch(cells, "scroll_x", self._scrolled_x)
        self.watch(cells, "scroll_y", self._scrolled_y)

    def _scrolled_x(self, x: float) -> None:
        self.query_one("#locale-strip").scroll_to(x=x, animate=False, force=True, immediate=True)

    def _scrolled_y(self, y: float) -> None:
        self.query_one("#file-column").scroll_to(y=y, animate=False, force=True, immediate=True)

    def counts(self, texts: Sequence[str]) -> None:
        """`texts` beside the locales' names, one a locale."""
        heads = self.query(".column-head-count").results(Static)
        for head, text in zip(heads, texts, strict=True):
            head.update(text)

    def cell(self, file: str, locale: str) -> GridCell | None:
        """The cell of `file` in `locale`; None when the grid has no such file or locale."""
        if file not in self._files or locale not in self._locales:
            return None
        locales = list(self._locales)
        return self._cells[self._files.index(file) * len(locales) + locales.index(locale)]

    @on(GridCell.Moved)
    def _moved(self, event: GridCell.Moved) -> None:
        event.stop()
        locales = list(self._locales)
        row = self._files.index(event.cell.file) + event.rows
        column = locales.index(event.cell.locale) + event.columns
        if 0 <= row < len(self._files) and 0 <= column < len(locales):
            cell = self.cell(self._files[row], locales[column])
            if cell is not None:
                cell.focus()
                cell.scroll_visible()
