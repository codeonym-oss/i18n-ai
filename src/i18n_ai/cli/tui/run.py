from rich.console import Console
from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import VerticalScroll
from textual.screen import Screen
from textual.widgets import Footer, Header, Log, ProgressBar, Static

from ...application.exports.locale import GenerationReceipt
from ..rendering import render_receipt
from .progress import TuiProgress


class RunScreen(Screen[None]):
    """A generation as it runs: a bar and a line per file and locale done; then its receipt,
    and the command that runs it again."""

    DEFAULT_CSS = """
    RunScreen #jobs { height: auto; max-height: 10; border: round $panel; }
    RunScreen #receipt { padding: 1 0; }
    """
    BINDINGS = [
        Binding("b", "back", "Back to setup"),
        Binding("q", "app.quit", "Quit"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.done = False

    def compose(self) -> ComposeResult:
        yield Header()
        with VerticalScroll():
            yield ProgressBar(id="progress", show_eta=False)
            yield Log(id="jobs")
            yield Static("", id="receipt")
        yield Footer()

    def on_tui_progress_started(self, message: TuiProgress.Started) -> None:
        self.query_one(ProgressBar).update(total=message.jobs)

    def on_tui_progress_dropped(self, message: TuiProgress.Dropped) -> None:
        self.query_one(ProgressBar).advance(message.jobs)
        self.query_one(Log).write_line(f"left out: {message.reason}")

    def on_tui_progress_advanced(self, message: TuiProgress.Advanced) -> None:
        self.query_one(ProgressBar).advance(1)
        self.query_one(Log).write_line(message.description)

    def show_receipt(self, receipt: GenerationReceipt, again: str) -> None:
        """The table the CLI prints, and the command that runs it again without the TUI."""
        console = Console(width=max(self.app.size.width - 2, 60), highlight=False)
        with console.capture() as capture:
            render_receipt(console, receipt)
            console.print(f"\nTo run it again: [bold]{again}[/]")
        self._end(Text.from_ansi(capture.get()))

    def stopped(self, reason: str) -> None:
        self._end(Text(f"The run stopped: {reason}", style="red"))

    def _end(self, content: Text) -> None:
        self.query_one("#receipt", Static).update(content)
        self.done = True
        self.refresh_bindings()

    def check_action(self, action: str, parameters: tuple[object, ...]) -> bool | None:
        # Back, once the run is over
        return self.done if action == "back" else True

    def action_back(self) -> None:
        self.dismiss()
