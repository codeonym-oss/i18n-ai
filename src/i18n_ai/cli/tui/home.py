from pathlib import Path

from rich.markup import escape
from textual import events, on, work
from textual.app import ComposeResult
from textual.containers import Grid, Horizontal, Vertical
from textual.content import Content
from textual.widget import Widget
from textual.widgets import Static

from ...application.exports.locale import (
    FallbackView,
    ListFallbacksQuery,
    ScanLocaleTreeQuery,
    ScanReport,
    TargetFileView,
)
from ...domain.exports.locale import LocaleCode, SourceLocaleUnknown
from .aurora import HEAT
from .kit.heat import HeatCell, percent
from .kit.shell import ShellScreen
from .kit.widgets import Card, KpiTile
from .plan import count
from .refusals import REFUSALS

NO_TREE = "No locale tree found here · ctrl+n to set one up"
NO_SOURCE = "This tree does not tell its source locale · ctrl+n to pick it in a new run"


class HomeScreen(ShellScreen[None]):
    """The tree at a glance, from its scan and its fallback record: four figures, how much of
    each target file is translated, and the fallbacks waiting for a review."""

    DEFAULT_CSS = """
    HomeScreen #home { height: auto; }
    HomeScreen #home-empty { width: 1fr; height: 1fr; content-align: center middle; }
    HomeScreen #kpis { grid-size: 4; grid-gutter: 0 1; grid-rows: auto; height: auto; }
    HomeScreen.-narrow #kpis { grid-size: 2; }
    HomeScreen #coverage { margin-top: 1; }
    HomeScreen #heatmap { grid-gutter: 0 1; grid-rows: 1; height: auto; margin-top: 1; }
    HomeScreen .heat-head { color: $text-muted; }
    HomeScreen .heat-total { text-align: right; text-style: bold; }
    HomeScreen #legend { margin-top: 1; color: $text-muted; }
    HomeScreen #banner {
        height: 3; margin-top: 1; padding: 0 2; border: round $warning-border;
        background: $warning-surface;
    }
    HomeScreen #banner > Static { width: auto; height: 1; }
    HomeScreen #banner-glyph { color: $warning; padding-right: 2; }
    HomeScreen #banner-text { text-style: bold; }
    HomeScreen #banner-review { color: $warning; dock: right; }
    """
    SECTION = "home"

    def body(self) -> ComposeResult:
        yield Static("", id="home-empty", markup=False)
        yield Vertical(id="home")
        with Horizontal(id="banner"):
            yield Static("◐", id="banner-glyph")
            yield Static("", id="banner-text")
            yield Static("Review [b]v[/b]", id="banner-review")

    def on_mount(self) -> None:
        self.watch(self.app, "locale_tree", self._tree_switched, init=False)
        self._empty(None)
        self.query_one("#banner").display = False

    def on_screen_resume(self) -> None:
        # Back from a run or a review, the record may have changed
        self._load()

    def _tree_switched(self) -> None:
        self._load()

    @work(exclusive=True, group="home")
    async def _load(self) -> None:
        request = self.shell.tree_request()
        if request is None:
            await self._show(None, (), NO_TREE)
            return
        mediator = self.shell.mediator
        try:
            first = await mediator.send(ScanLocaleTreeQuery(request))
            targets = tuple(LocaleCode(code) for code in first.existing if code != first.source)
            report = await mediator.send(ScanLocaleTreeQuery(request, targets))
            entries = (await mediator.send(ListFallbacksQuery(request))).entries
        except SourceLocaleUnknown:
            await self._show(None, (), NO_SOURCE)
            return
        except REFUSALS as error:
            await self._show(None, (), error.message)
            return
        await self._show(report, entries, None)

    async def _show(
        self, report: ScanReport | None, entries: tuple[FallbackView, ...], empty: str | None
    ) -> None:
        self.shell.fallbacks = len(entries)
        self._empty(empty)
        home = self.query_one("#home")
        await home.remove_children()
        banner = self.query_one("#banner")
        banner.display = bool(entries)
        if report is None:
            return
        await home.mount_all([_figures(report, entries), _coverage(report, entries)])
        one = len(entries) == 1
        text = f"{count(len(entries), 'fallback')} kept {'its' if one else 'their'} source text"
        self.query_one("#banner-text", Static).update(text)

    def _empty(self, text: str | None) -> None:
        empty = self.query_one("#home-empty", Static)
        empty.display = text is not None
        empty.update(text or "")
        self.query_one("#home").display = text is None

    @on(events.Click, "#banner")
    def _review(self) -> None:
        self.shell.action_review()


def _figures(report: ScanReport, entries: tuple[FallbackView, ...]) -> Grid:
    cells = [cell for target in report.targets for cell in target.files]
    done = sum(cell.reusable for cell in cells)
    total = done + sum(cell.to_translate for cell in cells)
    files = report.qualified
    codes = " ".join(target.locale for target in report.targets) or "none yet"
    return Grid(
        KpiTile(
            "COVERAGE",
            f"{percent(done, total)}%" if total else "—",
            "translated, all locales",
        ),
        KpiTile(
            "MESSAGES",
            str(sum(file.messages for file in files)),
            f"in the source, {count(len(files), 'file')}",
        ),
        KpiTile(
            "FALLBACKS",
            str(len(entries)),
            "kept their source text",
            tone="warning" if entries else "",
        ),
        KpiTile("LOCALES", str(len(report.targets)), f"{report.source} → {codes}"),
        id="kpis",
    )


def _coverage(report: ScanReport, entries: tuple[FallbackView, ...]) -> Card:
    """A row per target locale, a column per file: each cell's share of messages translated,
    and its fallbacks."""
    files = [file.name for file in report.qualified]
    cells: list[Widget] = [Static(""), *(_head(name) for name in files), _head("TOTAL", "total")]
    for target in report.targets:
        by_file = {cell.file: cell for cell in target.files}
        locale = f"[b $primary]{target.locale}[/] [$text-muted]{escape(target.name)}[/]"
        cells.append(Static(Content.from_markup(locale)))
        for name in files:
            cell = by_file.get(name)
            if cell is None:
                cells.append(HeatCell(0))
                continue
            fallen = sum(_in(view, cell, report.output) for view in entries)
            share = percent(cell.reusable, cell.reusable + cell.to_translate)
            cells.append(HeatCell(share, f"◐ {fallen}" if fallen else ""))
        done = sum(cell.reusable for cell in target.files)
        messages = done + target.to_translate
        cells.append(Static(f"{done}/{messages}", classes="heat-total"))
    grid = Grid(*cells, id="heatmap")
    grid.styles.grid_size_columns = len(files) + 2
    grid.set_styles(f"grid-columns: 16 {' '.join('1fr' for _ in files)} 9;")
    scale = " ".join(f"[{background}]██[/]" for background, _ in HEAT)
    legend = Static(f"0% {scale} 100%   [$warning]◐ has fallbacks[/]", id="legend")
    layout = f"{report.source} → {count(len(report.targets), 'locale')} × "
    card = Card(grid, legend, title="Coverage", id="coverage")
    card.border_subtitle = escape(layout + count(len(files), "file"))
    return card


def _head(text: str, kind: str = "") -> Static:
    return Static(escape(text), classes=f"heat-head heat-{kind}" if kind else "heat-head")


def _in(view: FallbackView, cell: TargetFileView, output: Path) -> bool:
    """Whether the fallback is in the target file of `cell`: the record keeps its file relative
    to the tree's output, and its key in a bundle."""
    try:
        file = cell.path.resolve().relative_to(output.resolve()).as_posix()
    except ValueError:
        return False
    return view.entry.file.as_posix() == file and view.entry.key == cell.bundle_key
