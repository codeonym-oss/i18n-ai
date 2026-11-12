import time
from collections.abc import Callable, Iterable

from rich.markup import escape
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Grid, Horizontal, Vertical, VerticalScroll
from textual.content import Content
from textual.timer import Timer
from textual.widget import Widget
from textual.widgets import Static

from ...application.exports.locale import (
    FileDropped,
    FileResult,
    GenerationReceipt,
    JobDone,
    JobRetrying,
    JobStarted,
    ResultStatus,
    RunStarted,
    ScanReport,
)
from ..common.setup import Planned, within
from ..rendering import LISTED
from .kit.grid import CellGrid
from .kit.heat import progress
from .kit.shell import WIDE, ShellScreen
from .kit.widgets import Card, KpiTile, RunCell
from .plan import count
from .progress import TuiProgress

FEED_SHORT = 8  # the feed's height under the grid, on a narrow terminal

# A finished job's state, by its result's status
STATE_OF = {
    ResultStatus.WRITTEN: "written",
    ResultStatus.PARTIAL: "partial",
    ResultStatus.REFUSED: "refused",
    ResultStatus.FAILED: "failed",
    ResultStatus.IGNORED: "ignored",
}
# A feed line's glyph colour, by the state it says
TONES = {
    "run": "$primary",
    "translating": "$secondary",
    "retry": "$warning",
    "written": "$success",
    "partial": "$warning",
    "refused": "$warning",
    "failed": "$error",
    "ignored": "$text-muted",
    "stopped": "$error",
}
PROBLEMS = {"retry", "partial", "refused", "failed", "ignored", "stopped"}
PARTLY = ("partial", "refused")  # written with fallbacks, or not written for them
WROTE = ("written", "partial")  # the states whose file was written


class RunScreen(ShellScreen[None]):
    """A generation as it runs: its progress in messages, the plan's grid with each job live
    (waiting, translating, retrying, then what became of it), and every event in a feed, the
    problems popping up too. Once over, it is the receipt: the figures, the grid, the feed, and
    the command that runs it again."""

    DEFAULT_CSS = """
    RunScreen #run { height: 1fr; }
    RunScreen #run-main { width: 1fr; height: 1fr; }
    RunScreen #progress-row { height: auto; }
    RunScreen #done-block { width: 12; height: auto; }
    RunScreen #progress-bars { width: 1fr; height: auto; }
    RunScreen #bar { height: 1; }
    RunScreen #tiles { grid-size: 4; grid-gutter: 0 1; grid-rows: auto; height: auto; }
    RunScreen #events { width: 44; margin-left: 1; }
    RunScreen #feed { height: 1fr; }
    RunScreen #feed.-problems .event { display: none; }
    RunScreen #feed.-problems .event.-problem { display: block; }
    RunScreen.-narrow #run { layout: vertical; }
    RunScreen.-narrow #events { width: 1fr; margin: 0; }
    RunScreen.-narrow #done-block { display: none; }
    RunScreen.-narrow #progress-bars { layout: horizontal; }
    RunScreen.-narrow #bar { width: 1fr; min-width: 8; margin-right: 1; }
    RunScreen.-narrow #progress-line { width: auto; }
    RunScreen.-narrow #tiles { grid-size: 2; }
    """
    BINDINGS = [
        Binding("ctrl+c", "stop", "Stop"),
        Binding("p", "problems", "Problems"),
        Binding("y", "copy", "Copy command"),
        Binding("v", "review", "Review"),
        Binding("b", "back", "Back to setup"),
        Binding("q", "app.quit", "Quit"),
    ]
    AUTO_FOCUS = "RunCell"
    SECTION = "run"

    def __init__(
        self,
        report: ScanReport,
        plan: Planned,
        tree: str,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        super().__init__()
        self._tree = tree
        self._clock = clock
        self.done = False
        self.stop: Callable[[], None] | None = None  # the setup's, to cancel the run
        self._files = [file.name for file in report.qualified]
        self._locales = {target.locale: target.name for target in report.targets}
        self._source = report.source
        self._messages = {file.name: file.messages for file in report.qualified}
        self._off = plan.off
        # Each job's planned messages: what it counts once it ends
        self._planned = {
            (file.file, target.locale): file.to_translate
            for target in report.targets
            for file in target.files
            if (file.file, target.locale) not in plan.off
        }
        self._jobs = len(self._planned)
        self._total = sum(self._planned.values())
        self._ended: dict[tuple[str, str], str] = {}  # a finished job's state
        self._attempts: dict[tuple[str, str], int] = {}
        self._retries = 0
        self._outcome = {"written": 0, "partial": 0, "failed": 0}  # messages, by outcome
        self._start = clock()
        self._stopped_at: float | None = None
        self._timer: Timer | None = None
        self._again: str | None = None
        self._review: Callable[[], None] | None = None

    def body(self) -> ComposeResult:
        with Horizontal(id="run"):
            with Vertical(id="run-main"):
                with Card(title="Progress", id="progress"), Horizontal(id="progress-row"):
                    with Vertical(id="done-block"):
                        yield Static("DONE", id="done-label")
                        yield Static("", id="done-percent")
                    with Vertical(id="progress-bars"):
                        yield _Bar()
                        yield Static("", id="progress-line")
                with Card(title="Jobs", id="grid-card").add_class("-fill"):
                    yield CellGrid(
                        self._files,
                        self._locales,
                        {
                            f: f"{count(self._messages[f], 'message')} in {self._source}"
                            for f in self._files
                        },
                        [RunCell(f, locale) for f in self._files for locale in self._locales],
                    )
                with Card(title="Run it again", id="again").add_class("-accent"):
                    yield Static("", id="again-text")
            with Card(title="Events · all", id="events"):
                yield VerticalScroll(id="feed", can_focus=False)

    def on_mount(self) -> None:
        crumb = Content.from_markup("[$text-muted]New run /[/] [b]Run[/b]")
        self.query_one("#crumb", Static).update(crumb)
        self.query_one("#again").display = False
        for cell in self.query(RunCell):
            pair = (cell.file, cell.locale)
            if pair in self._off:
                cell.show("off")
            else:
                cell.show("waiting", detail=f"{self._planned.get(pair, 0)} to translate")
        self._progress()
        self._timer = self.set_interval(1, self._progress)

    def status_tree(self) -> str:
        # A run keeps the tree it started on, whichever the app is on
        if self.done:
            return self._tree
        line = f"{self._done()}/{self._jobs} jobs · {self._time()}  ·  {self._tree}"
        # Narrow, the keys need the room, and the section's chip says it runs
        return line if self.has_class("-narrow") else f"RUNNING · {line}"

    def _fit(self, width: int, height: int) -> None:
        super()._fit(width, height)
        # Beside the grid the feed takes the height; under it, a few lines
        self.query_one("#events").styles.height = "1fr" if width >= WIDE else FEED_SHORT
        self._progress()

    # The events

    def on_tui_progress_event(self, message: TuiProgress.Event) -> None:
        match message.event:
            case RunStarted(jobs):
                self._jobs = jobs
                line = f"{count(jobs, 'job')} · {count(self._total, 'message')}"
                self._feed("run", "run started", line)
            case JobStarted(file, locale):
                if cell := self._cell(file, locale):
                    planned = self._planned.get((file, locale), 0)
                    cell.show("translating", detail=f"{planned} to translate")
                self._feed("translating", f"{file} → {locale}", "translating")
            case JobRetrying(file, locale, messages, attempt, attempts):
                self._retries += 1
                self._attempts[(file, locale)] = attempt
                if cell := self._cell(file, locale):
                    cell.show(
                        "retry", f"{attempt}/{attempts}", f"{count(messages, 'message')} sent back"
                    )
                line = f"{count(messages, 'message')} sent back · attempt {attempt}/{attempts}"
                self._feed("retry", f"{file} → {locale}", line)
            case JobDone(result):
                if result.target is not None:
                    self._finished(result)
            case FileDropped(file, jobs, reason):
                self._dropped(file, jobs, reason)
        self._progress()

    def _finished(self, result: FileResult) -> None:
        pair = (result.file, str(result.target))
        state = STATE_OF[result.status]
        self._ended[pair] = state
        outcome = "partial" if state in PARTLY else state
        if outcome in self._outcome:
            self._outcome[outcome] += self._planned.get(pair, 0)
        fallbacks = len({violation.path for violation in result.failures})
        if state == "failed":
            detail = result.reason or "failed"
        elif state in PARTLY:
            detail = f"{result.translated} translated · {count(fallbacks, 'fallback')}"
        else:
            detail = f"{result.translated} translated · {result.reused} kept"
        attempts = self._attempts.get(pair, 1)
        note = f"after {count(attempts, 'attempt')}" if attempts > 1 else ""
        if cell := self._cell(*pair):
            cell.show(state, detail=detail, note=note)

        job = f"{result.file} → {result.target}"
        lines: list[str] = []
        if state == "written":
            line = f"written · {result.translated} translated, {result.reused} kept"
            if result.path is not None:
                line += f" · {within(self.shell.project)(result.path)}"
        elif state == "failed":
            line = f"failed · {result.reason}"
        else:
            line = f"{state} · {count(fallbacks, 'fallback')}"
        lines += _listed(f"{v.path} · {v.message}" for v in result.failures)
        if result.warnings:
            lines.append(f"! {count(len(result.warnings), 'warning')}")
            lines += _listed(f"{v.path} · {v.message}" for v in result.warnings)
        self._feed(state, job, line, lines, problem=bool(result.warnings) or None)
        if state in (*PARTLY, "failed"):
            first = result.reason if state == "failed" else _first(result)
            self.notify(
                first or "",
                title=f"{job} is {state}",
                severity="error" if state == "failed" else "warning",
            )
        self._heads()

    def _dropped(self, file: str, jobs: int, reason: str) -> None:
        self._jobs -= jobs
        for locale in self._locales:
            pair = (file, locale)
            if pair in self._planned:
                self._total -= self._planned[pair]
                self._ended[pair] = "ignored"
                if cell := self._cell(file, locale):
                    cell.show("ignored", detail=reason)
        self._feed("ignored", file, f"ignored · {reason}")
        self.notify(reason, title=f"{file} is ignored", severity="warning")
        self._heads()

    # What the screen shows

    def _cell(self, file: str, locale: str) -> RunCell | None:
        """The cell of `file` in `locale`; None for a file added since the plan, which the run
        translates but the grid does not show."""
        cell = self.query_one(CellGrid).cell(file, locale)
        return cell if isinstance(cell, RunCell) else None

    def _done(self) -> int:
        return sum(1 for state in self._ended.values() if state != "ignored")

    def _time(self) -> str:
        seconds = int((self._stopped_at or self._clock()) - self._start)
        return f"{seconds // 60:02}:{seconds % 60:02}"

    def _progress(self) -> None:
        """The progress card and the status line, from the jobs ended so far and the time."""
        if not self.is_mounted:
            return
        ended = sum(self._outcome.values())
        share = ended * 100 // self._total if self._total else (100 if self.done else 0)
        self.query_one("#done-percent", Static).update(f"{share}%")
        bar = self.query_one(_Bar)
        bar.counts = (
            self._outcome["written"],
            self._outcome["partial"],
            self._outcome["failed"],
            self._total,
        )
        bar.refresh()
        states = list(self._ended.values())
        partial = sum(1 for state in states if state in PARTLY)
        line = (
            f"[b]{self._done()}[/b][$text-muted]/{self._jobs} jobs[/] · "
            f"[b]{ended}[/b][$text-muted]/{self._total} messages[/] · "
            f"[$warning]⟳ {self._retries}[/] [$warning]◐ {partial}[/] "
            f"[$error]✕ {states.count('failed')}[/] · {self._time()}"
        )
        if self.has_class("-narrow"):
            line = f"[b]{share}%[/b] · {line}"
        self.query_one("#progress-line", Static).update(Content.from_markup(line))
        self.query_one("#status-tree", Static).update(self.status_tree())

    def _heads(self) -> None:
        """Each locale's files written of its jobs, beside its name; a dropped file's leave."""
        texts = []
        for locale in self._locales:
            jobs = [
                pair
                for pair in self._planned
                if pair[1] == locale and self._ended.get(pair) != "ignored"
            ]
            written = sum(1 for pair in jobs if self._ended.get(pair) in WROTE)
            texts.append(f"{written}/{len(jobs)}")
        self.query_one(CellGrid).counts(texts)

    def _feed(
        self,
        state: str,
        job: str,
        text: str,
        lines: list[str] | None = None,
        problem: bool | None = None,
    ) -> None:
        """A line on top of the feed: the time, the state's glyph, the job and `text`, then
        `lines` under it; a problem when its state is one, or when `problem` says so."""
        glyph = "◆" if state == "run" else RunCell.STATES[state][0]
        markup = (
            f"[$text-muted]{self._time()}[/] [{TONES[state]}]{glyph}[/] [b]{escape(job)}[/b]\n"
            f"[$text-muted]{escape(text)}[/]"
        )
        markup += "".join(f"\n  {escape(line)}" for line in lines or ())
        line = Static(Content.from_markup(markup), classes="event")
        line.set_class(problem if problem is not None else state in PROBLEMS, "-problem")
        feed = self.query_one("#feed", VerticalScroll)
        feed.mount(line, before=0 if feed.children else None)

    # The end

    def show_receipt(
        self,
        receipt: GenerationReceipt,
        again: str,
        note: str | None = None,
        review: Callable[[], None] | None = None,
        left: int = 0,
    ) -> None:
        """The run's figures in the progress card's place, and the command that runs it again
        without the TUI, with `note` saying where it differs from the run; `review` opens the
        review of the `left` fallbacks it left, when it left some."""
        self._review = review
        results = [result for result in receipt.results if result.target is not None]
        written = [r for r in results if r.status in (ResultStatus.WRITTEN, ResultStatus.PARTIAL)]
        fallbacks = sum(len({v.path for v in r.failures}) for r in results)
        failed = sum(1 for r in results if r.status == ResultStatus.FAILED)
        tiles = Grid(
            KpiTile("FILES WRITTEN", str(len(written)), f"of {count(len(results), 'job')}"),
            KpiTile(
                "TRANSLATED",
                str(sum(r.translated for r in results)),
                f"messages · {sum(r.reused for r in results)} kept",
            ),
            KpiTile(
                "FALLBACKS",
                str(fallbacks),
                "recorded for the next run" if fallbacks else "none",
                "warning" if fallbacks else "",
            ),
            KpiTile("FAILED", str(failed), "see the events" if failed else "nothing to retry"),
            id="tiles",
        )
        self.query_one("#run-main").mount(tiles, before=self.query_one("#progress"))
        self.query_one("#progress").display = False
        self._feed("run", "run finished", f"Generated with {receipt.model}")
        self.notify(
            f"{count(len(written), 'file')} written · {count(fallbacks, 'fallback')}",
            title="The run is over",
        )
        self._show_again(again, note, left if review is not None else 0)
        self._end()

    def halted(self, again: str, note: str | None = None) -> None:
        """Stopped by hand: the jobs not over are stopped; what is written stays. Nothing to show
        when the app is quitting and the screen already gone."""
        if not self.is_mounted:
            return
        for pair in self._planned:
            if pair not in self._ended and (cell := self._cell(*pair)):
                cell.show("stopped")
        line = f"{self._done()} of {count(self._jobs, 'job')} done"
        self._feed("stopped", "stopped", line)
        self.notify(f"{line}; what is written stays.", title="The run stopped", severity="warning")
        self._show_again(again, note, 0)
        self._end()

    def stopped(self, reason: str) -> None:
        self._feed("failed", "the run stopped", reason)
        self.notify(reason, title="The run stopped", severity="error")
        again = self.query_one("#again", Card)
        again.border_title = "Stopped"
        again.display = True
        line = f"[$error]The run stopped: {escape(reason)}[/]"
        self.query_one("#again-text", Static).update(Content.from_markup(line))
        self._end()

    def _show_again(self, again: str, note: str | None, left: int) -> None:
        self._again = again
        lines = [f"[$success]$[/] {escape(again)}"]
        if note is not None:
            lines.append(f"[$text-muted]{escape(note)}[/]")
        keys = "[b]y[/b] copy"
        if left:
            keys += f" · [b]v[/b] review {count(left, 'fallback')}"
        lines.append(keys)
        self.query_one("#again-text", Static).update(Content.from_markup("\n".join(lines)))
        self.query_one("#again").display = True

    def _end(self) -> None:
        self._stopped_at = self._clock()
        if self._timer is not None:
            self._timer.stop()
        self.done = True
        self._progress()
        self.refresh_bindings()

    # Keys

    @property
    def reviewable(self) -> bool:
        return self.done and self._review is not None

    def check_action(self, action: str, parameters: tuple[object, ...]) -> bool | None:
        # Stop while it runs; Back, once it is over; Copy, when there is a command; Review,
        # when it left fallbacks
        if action == "stop":
            return not self.done
        if action == "copy":
            return self._again is not None
        if action == "review":
            return self.reviewable
        return self.done if action == "back" else True

    def action_stop(self) -> None:
        if self.stop is not None:
            self.stop()

    def action_problems(self) -> None:
        feed = self.query_one("#feed")
        feed.toggle_class("-problems")
        which = "problems" if feed.has_class("-problems") else "all"
        self.query_one("#events", Card).border_title = f"Events · {which}"

    def action_copy(self) -> None:
        if self._again is not None:
            self.app.copy_to_clipboard(self._again)
            self.notify("The command is copied.")

    def action_review(self) -> None:
        if self._review is not None:
            self._review()

    def action_back(self) -> None:
        self.dismiss()


class _Bar(Widget):
    """The run's messages as a bar, drawn at its width."""

    def __init__(self) -> None:
        super().__init__(id="bar")
        self.counts = (0, 0, 0, 0)

    def render(self) -> Content:
        return progress(self.size.width, *self.counts)


def _listed(lines: Iterable[str]) -> list[str]:
    """The first `LISTED` of `lines`, then how many more."""
    every = list(lines)
    shown = every[:LISTED]
    if len(every) > LISTED:
        shown.append(f"… and {len(every) - LISTED} more")
    return shown


def _first(result: FileResult) -> str:
    """The first key that fell back, and why."""
    if not result.failures:
        return ""
    violation = result.failures[0]
    more = len(result.failures) - 1
    return f"{violation.path} kept its source: {violation.message}" + (
        f" (+{more} more)" if more else ""
    )
