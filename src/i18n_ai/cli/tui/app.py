"""`i18n-ai` at a terminal: a generation set up as a form, run, and its receipt, full screen.
Every query and command goes through the mediator, in Textual's loop; nothing prints on the
terminal it draws on: the console is quiet, the progress is the TUI's own, and the logs go to
Textual's."""

import logging
from collections.abc import Iterable
from pathlib import Path

from rich.console import Console
from textual.app import App, SystemCommand
from textual.binding import Binding
from textual.logging import TextualHandler
from textual.screen import Screen

from ...di import Bootstrap
from ...runtime.answers import load_answers
from ...runtime.settings import Settings
from .progress import TuiProgress
from .run import RunScreen
from .setup import SetupScreen


class I18nAiApp(App[None]):
    TITLE = "i18n-ai"
    BINDINGS = [Binding("q", "quit", "Quit")]

    def __init__(self, settings: Settings, project: Path) -> None:
        super().__init__()
        self.project = project
        self.progress = TuiProgress()
        self._quiet = Console(quiet=True)
        self._bootstrap = Bootstrap(settings, self._quiet, progress=self.progress)

    async def on_mount(self) -> None:
        await self._bootstrap.__aenter__()
        await self.push_screen(
            SetupScreen(
                self._bootstrap.mediator,
                self._quiet,
                self._bootstrap.settings.generation,
                self.progress,
                self.project,
                load_answers(self.project),
            )
        )

    async def on_unmount(self) -> None:
        # A run quit midway stops before the container closes under it
        self.workers.cancel_all()
        await self.workers.wait_for_complete()
        await self._bootstrap.__aexit__(None, None, None)

    def get_system_commands(self, screen: Screen[object]) -> Iterable[SystemCommand]:
        if isinstance(screen, SetupScreen):
            yield SystemCommand("Run", "Generate the targets the form sets up", screen.action_run)
        if isinstance(screen, RunScreen) and screen.done:
            yield SystemCommand(
                "Back to setup", "Change the form, and run again", screen.action_back
            )
        yield from super().get_system_commands(screen)


def run_tui(settings: Settings, project: Path) -> None:
    """Run the TUI, its logs in Textual's own while it draws on the terminal."""
    root = logging.getLogger()
    handlers = root.handlers[:]
    root.handlers = [TextualHandler()]
    try:
        I18nAiApp(settings, project).run()
    finally:
        root.handlers = handlers
