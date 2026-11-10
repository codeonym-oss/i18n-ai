"""`i18n-ai` at a terminal: a generation set up as a form, run, and its receipt, full screen.
Every query and command goes through the mediator, in Textual's loop; nothing prints on the
terminal it draws on: the console is quiet, the progress is the TUI's own, and the logs go to
Textual's."""

import logging
from collections.abc import Callable, Iterable
from pathlib import Path

from mediary import Mediator
from rich.console import Console
from textual.app import App, SystemCommand
from textual.binding import Binding
from textual.logging import TextualHandler
from textual.reactive import reactive
from textual.screen import Screen
from textual.widgets import Select

from ...application.ports.locale import TreeRequest
from ...di import Bootstrap
from ...domain.exports.provider import ModelSpec
from ...runtime.answers import load_answers
from ...runtime.settings import Settings
from ..common.setup import generation_options, within
from .aurora import AURORA
from .home import HomeScreen
from .plan import PlanScreen
from .progress import TuiProgress
from .refusals import REFUSALS
from .review import ReviewScreen
from .run import RunScreen
from .setup import SetupScreen
from .trees import Trees, find_trees


class I18nAiApp(App[None]):
    """Three sections, each a mode with its own screens: Home, the tree at a glance; Run, the
    setup, its plan and the run; Review, the fallbacks of a tree."""

    TITLE = "i18n-ai"
    CSS_PATH = "aurora.tcss"
    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("ctrl+o", "home", "Home", show=False),
        Binding("ctrl+n", "new_run", "Run", show=False),
        Binding("v", "review", "Review", show=False),
    ]

    locale_tree: reactive[str | None] = reactive(None)  # the tree Home shows, as setup lists it
    fallbacks = reactive(0)  # recorded beside it

    def __init__(self, settings: Settings, project: Path) -> None:
        super().__init__()
        self.register_theme(AURORA)
        self.theme = AURORA.name
        self.project = project
        self.progress = TuiProgress()
        self.trees = Trees()
        self._quiet = Console(quiet=True)
        self._bootstrap = Bootstrap(settings, self._quiet, progress=self.progress)
        self._last = load_answers(project)
        self._back = "home"  # the section the review was opened from

    async def on_mount(self) -> None:
        await self._bootstrap.__aenter__()
        try:
            self.trees = await find_trees(
                self._bootstrap.mediator, self._quiet, self.project, self._last
            )
        except REFUSALS as error:
            self.notify(error.message, severity="error")
        if self.trees.preset_name is not None:
            self.sub_title = f"{self.trees.preset_name} preset"
        first = self.trees.choices[0].value if self.trees.choices else None
        self.locale_tree = self.trees.default or first
        self.add_mode("home", HomeScreen)
        self.add_mode("run", self._setup)
        self.add_mode("review", self._plain_review)
        await self.switch_mode("home")

    def watch_locale_tree(self, tree: str | None) -> None:
        """Another tree for Home, the review and a setup not yet run; a run going keeps its
        own."""
        if not self.current_mode or self.current_mode == "_default":
            return  # the sections are not there yet
        if self.current_mode == "review":
            self.switch_screen(self._plain_review())
        else:
            self.remove_mode("review")
            self.add_mode("review", self._plain_review)
        try:
            stack = self.get_screen_stack("run")
        except KeyError:
            return  # the setup starts on it when first shown
        if len(stack) == 1 and isinstance(stack[0], SetupScreen) and tree is not None:
            stack[0].query_one("#tree", Select).value = tree

    async def on_unmount(self) -> None:
        # A run quit midway stops before the container closes under it
        self.workers.cancel_all()
        await self.workers.wait_for_complete()
        await self._bootstrap.__aexit__(None, None, None)

    @property
    def mediator(self) -> Mediator:
        return self._bootstrap.mediator

    def tree_request(self) -> TreeRequest | None:
        """The request for the tree Home shows, None when the project has none."""
        if self.locale_tree is None:
            return None
        return self.trees.request(self.locale_tree, within(self.project), self._last)

    def _setup(self) -> SetupScreen:
        return SetupScreen(
            self._bootstrap.mediator,
            self._quiet,
            self._bootstrap.settings.generation,
            self.progress,
            self.project,
            self._last,
            self.trees,
            self.locale_tree,
        )

    def _plain_review(self) -> ReviewScreen:
        """The review of Home's tree, with the model picked last, else the settings' one."""
        model = self._last.model or self._bootstrap.settings.generation.model
        request = self.tree_request() or TreeRequest(Path())
        return self._review(request, ModelSpec(model) if model else None)

    def _review(self, tree: TreeRequest, model: ModelSpec | None) -> ReviewScreen:
        options = generation_options(self._bootstrap.settings.generation)
        return ReviewScreen(self._bootstrap.mediator, tree, model, options)

    def open_review(self, tree: TreeRequest, model: ModelSpec | None) -> None:
        """The Review section, on `tree`, retrying with `model`."""
        self._show_review(lambda: self._review(tree, model))

    def _show_review(self, screen: Callable[[], ReviewScreen]) -> None:
        self._back = self.current_mode
        self.remove_mode("review")
        self.add_mode("review", screen)
        self.switch_mode("review")

    def leave_review(self) -> None:
        """Back to the section the review was opened from."""
        self.switch_mode(self._back)

    def action_home(self) -> None:
        self.switch_mode("home")

    def action_new_run(self) -> None:
        self.switch_mode("run")

    def action_review(self) -> None:
        if self.current_mode != "review" and self.locale_tree is not None:
            self._show_review(self._plain_review)

    def get_system_commands(self, screen: Screen[object]) -> Iterable[SystemCommand]:
        if isinstance(screen, SetupScreen):
            yield SystemCommand("Plan", "See what the run will do, then run it", screen.action_plan)
            if screen.fallbacks:
                yield SystemCommand(
                    "Review fallbacks", "Edit, retry or accept them", screen.action_review
                )
        if isinstance(screen, PlanScreen):
            yield SystemCommand("Run", "Generate the cells that are on", screen.action_run)
        if isinstance(screen, RunScreen) and screen.done:
            yield SystemCommand(
                "Back to setup", "Change the form, and run again", screen.action_back
            )
        if isinstance(screen, RunScreen) and screen.reviewable:
            yield SystemCommand(
                "Review fallbacks", "Edit, retry or accept them", screen.action_review
            )
        # One theme: Textual's others are not offered
        yield from (c for c in super().get_system_commands(screen) if c.title != "Theme")


def run_tui(settings: Settings, project: Path) -> None:
    """Run the TUI, its logs in Textual's own while it draws on the terminal."""
    root = logging.getLogger()
    handlers = root.handlers[:]
    root.handlers = [TextualHandler()]
    try:
        I18nAiApp(settings, project).run()
    finally:
        root.handlers = handlers
