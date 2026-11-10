from collections.abc import Iterable
from typing import TYPE_CHECKING, ClassVar, cast

from textual import events, on
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.reactive import reactive
from textual.screen import Screen
from textual.widget import Widget
from textual.widgets import Footer, OptionList, Select, Static
from textual.widgets.option_list import Option

from .widgets import Chip

if TYPE_CHECKING:
    from ..app import I18nAiApp

# Each section: its glyph, its name, the app's action that opens it, and its chip's tone
SECTIONS = {
    "home": ("⌂", "Home", "home", "primary"),
    "run": ("▶", "Run", "new_run", "secondary"),
    "review": ("◐", "Review", "review", "warning"),
}
WIDE = 120  # columns, from which the sidebar shows its labels
SMALLEST = (80, 24)


class Sidebar(OptionList):
    """The app's sections, the screen's own highlighted; their glyphs alone when `narrow`.
    Review carries the fallbacks' count."""

    narrow = reactive(False)

    def __init__(self, section: str) -> None:
        super().__init__(id="sidebar", compact=True)
        self._section = section
        self._fallbacks = 0

    def on_mount(self) -> None:
        self.watch(self.app, "fallbacks", self._badge)

    def _badge(self, fallbacks: int) -> None:
        self._fallbacks = fallbacks
        self._show()

    def watch_narrow(self) -> None:
        self._show()

    def _show(self) -> None:
        options = []
        for name, (glyph, label, _, _) in SECTIONS.items():
            badge = str(self._fallbacks) if name == "review" and self._fallbacks else ""
            prompt = glyph if self.narrow else f"{glyph}  {label:<12}{badge:>4}"
            options.append(Option(prompt, id=name))
        self.set_options(options)
        self.highlighted = list(SECTIONS).index(self._section)

    @on(OptionList.OptionSelected)
    async def _picked(self, event: OptionList.OptionSelected) -> None:
        event.stop()
        await self.app.run_action(f"app.{SECTIONS[str(event.option_id)][2]}")


class ShellScreen[R](Screen[R]):
    """A screen in the app's frame: the sidebar, the command bar, its own body, and the status
    line with the section, the tree it is on and the keys. Below `WIDE` columns the sidebar is a
    rail; below `SMALLEST`, a notice takes the body's place."""

    SECTION: ClassVar[str] = "home"
    AUTO_FOCUS = "#body *"

    def compose(self) -> ComposeResult:
        glyph, label, _, tone = SECTIONS[self.SECTION]
        with Horizontal(id="frame"):
            yield Sidebar(self.SECTION)
            with Vertical(id="main"):
                with Horizontal(id="command-bar"):
                    yield Static(f"[$text-muted]Workspace /[/] [b]{label}[/]", id="crumb")
                    yield Static("⌕ [b]ctrl+p[/b]  commands", id="palette")
                    trees = ((choice.value, choice.value) for choice in self.shell.trees.choices)
                    yield Select[str](trees, id="switcher", prompt="Pick a tree", compact=True)
                with Vertical(id="body"):
                    yield from self.body()
                yield Static("", id="notice")
        with Horizontal(id="status"):
            yield Chip(glyph, label.upper(), tone, id="section")
            yield Static("", id="status-tree", markup=False)
            yield Footer(compact=True)

    def body(self) -> Iterable[Widget]:
        """The screen's own widgets, inside the frame."""
        return ()

    @property
    def shell(self) -> "I18nAiApp":
        return cast("I18nAiApp", self.app)

    def status_tree(self) -> str:
        """The tree the status line names: the app's, unless the screen is on its own."""
        return self.shell.locale_tree or "no tree"

    @on(events.Mount)
    def _framed(self) -> None:
        self.query_one("#switcher").display = len(self.shell.trees.choices) > 1
        self.watch(self.app, "locale_tree", self._tree_moved)
        self._fit(self.app.size.width, self.app.size.height)

    def _tree_moved(self, tree: str | None) -> None:
        if tree is not None:
            self.query_one("#switcher", Select).value = tree
        self.query_one("#status-tree", Static).update(self.status_tree())

    @on(Select.Changed, "#switcher")
    def _switched(self, event: Select.Changed) -> None:
        event.stop()
        if isinstance(event.value, str):
            self.shell.locale_tree = event.value

    @on(events.Resize)
    def _resized(self, event: events.Resize) -> None:
        self._fit(event.size.width, event.size.height)

    @on(events.ScreenResume)
    def _resumed(self) -> None:
        # The terminal may have changed size while another section showed
        self._fit(self.app.size.width, self.app.size.height)

    def _fit(self, width: int, height: int) -> None:
        self.set_class(width < WIDE, "-narrow")
        self.query_one(Sidebar).narrow = width < WIDE
        small = width < SMALLEST[0] or height < SMALLEST[1]
        self.set_class(small, "-small")
        notice = f"i18n-ai needs {SMALLEST[0]}×{SMALLEST[1]}; this terminal is {width}×{height}"
        self.query_one("#notice", Static).update(notice)

    @on(events.Click, "#palette")
    def _palette(self) -> None:
        self.app.action_command_palette()
