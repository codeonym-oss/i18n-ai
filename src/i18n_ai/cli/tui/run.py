from rich.console import Console
from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import VerticalScroll
from textual.screen import Screen
from textual.widgets import Footer, Header, Log, ProgressBar, Static

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
from ..common.setup import Planned
from ..rendering import render_receipt
from .grid import JobGrid
from .plan import count
from .progress import TuiProgress


class RunScreen(Screen[None]):
    """A generation as it runs: the plan's grid, each cell's atom live (waiting, translating,
    retrying, then what became of it), a bar, and the problems as they come; then its receipt,
    and the command that runs it again."""

    DEFAULT_CSS = """
    RunScreen #grid { height: auto; max-height: 1fr; }
    RunScreen #progress { padding: 1 1 0 1; }
    RunScreen #problems { height: auto; max-height: 8; border: round $panel; }
    RunScreen #receipt { padding: 1 0; }
    """
    BINDINGS = [
        Binding("b", "back", "Back to setup"),
        Binding("q", "app.quit", "Quit"),
    ]

    def __init__(self, report: ScanReport, plan: Planned) -> None:
        super().__init__()
        self.done = False
        self._files = [file.name for file in report.qualified]
        self._locales = [target.locale for target in report.targets]
        self._off = plan.off

    def compose(self) -> ComposeResult:
        yield Header()
        with VerticalScroll():
            yield JobGrid(self._files, self._locales, self._label, id="grid", cursor=False)
            yield ProgressBar(id="progress", show_eta=False)
            yield Log(id="problems")
            yield Static("", id="receipt")
        yield Footer()

    def on_mount(self) -> None:
        self.query_one("#problems").border_title = "Problems"
        self.query_one("#problems").display = False

    def _label(self, file: str, locale: str) -> str:
        return "off" if (file, locale) in self._off else "waiting"

    def on_tui_progress_event(self, message: TuiProgress.Event) -> None:
        grid = self.query_one(JobGrid)
        match message.event:
            case RunStarted(jobs):
                self.query_one(ProgressBar).update(total=jobs)
            case JobStarted(file, locale):
                grid.show(file, locale, "translating")
            case JobRetrying(file, locale, _, attempt, attempts):
                grid.show(file, locale, f"retry {attempt}/{attempts}")
            case JobDone(result):
                self.query_one(ProgressBar).advance(1)
                if result.target is not None:
                    grid.show(result.file, result.target, result.status.value)
                self._problem(result)
            case FileDropped(file, jobs, _):
                self.query_one(ProgressBar).advance(jobs)
                for locale in self._locales:
                    if (file, locale) not in self._off:
                        grid.show(file, locale, "ignored")

    def _problem(self, result: FileResult) -> None:
        """A line under Problems for an atom that failed, or left fallbacks."""
        if result.status == ResultStatus.FAILED:
            line = f"{result.file} → {result.target}: failed: {result.reason}"
        elif result.status in (ResultStatus.PARTIAL, ResultStatus.REFUSED):
            fallbacks = len({violation.path for violation in result.failures})
            line = f"{result.file} → {result.target}: {count(fallbacks, 'fallback')}"
        else:
            return
        problems = self.query_one("#problems", Log)
        problems.display = True
        problems.write_line(line)

    def show_receipt(self, receipt: GenerationReceipt, again: str, note: str | None = None) -> None:
        """The table the CLI prints, and the command that runs it again without the TUI, with
        `note` saying where it differs from the run."""
        console = Console(width=max(self.app.size.width - 2, 60), highlight=False)
        with console.capture() as capture:
            render_receipt(console, receipt)
            console.print(f"\nTo run it again: [bold]{again}[/]")
            if note is not None:
                console.print(note)
        self._end(Text.from_ansi(capture.get()))

    def stopped(self, reason: str) -> None:
        self._end(Text(f"The run stopped: {reason}", style="red"))

    def _end(self, content: Text) -> None:
        self.query_one(JobGrid).display = False
        self.query_one(ProgressBar).display = False
        self.query_one("#receipt", Static).update(content)
        self.done = True
        self.refresh_bindings()

    def check_action(self, action: str, parameters: tuple[object, ...]) -> bool | None:
        # Back, once the run is over
        return self.done if action == "back" else True

    def action_back(self) -> None:
        self.dismiss()
