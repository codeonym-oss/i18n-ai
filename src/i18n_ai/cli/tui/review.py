from mediary import Mediator
from rich.markup import escape
from textual import on, work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import ModalScreen, Screen
from textual.widgets import DataTable, Footer, Header, Input, Static

from ...application.exports.locale import (
    AcceptFallbacksCommand,
    FallbackView,
    GenerationOptions,
    ListFallbacksQuery,
    ResultStatus,
    RetryFallbacksCommand,
    SetMessageCommand,
)
from ...application.ports.locale import MessageRef, TreeRequest
from ...domain.exports.locale import errors
from ...domain.exports.provider import ModelSpec
from .plan import count
from .refusals import REFUSALS

STALE = "no longer in the source"


class ReviewScreen(Screen[None]):
    """The fallbacks a tree's runs left: each with its source, the model's rejected translation
    and the rules it broke. One is edited by hand; the marked ones (or the highlighted one) are
    translated again with the setup's model, or accepted as they are. An entry whose message is
    gone from the source can only be accepted."""

    DEFAULT_CSS = """
    ReviewScreen #fallbacks { height: auto; max-height: 1fr; }
    ReviewScreen #detail { padding: 1 1 0 1; }
    ReviewScreen #hint, ReviewScreen #empty { padding: 1 1 0 1; color: $text-muted; }
    """
    BINDINGS = [
        Binding("space", "mark", "Mark"),
        Binding("e", "edit", "Edit"),
        Binding("r", "retry", "Retry"),
        Binding("a", "accept", "Accept"),
        Binding("b,escape", "back", "Back"),
    ]

    def __init__(
        self,
        mediator: Mediator,
        tree: TreeRequest,
        model: ModelSpec | None,
        options: GenerationOptions,
    ) -> None:
        super().__init__()
        self._mediator = mediator
        self._tree = tree
        self._model = model
        self._options = options
        self._entries: tuple[FallbackView, ...] = ()
        self._marked: set[int] = set()

    def compose(self) -> ComposeResult:
        yield Header()
        yield DataTable[str](id="fallbacks", cursor_type="row")
        yield Static("", id="detail")
        yield Static("Pick a model in the setup to retry.", id="hint")
        yield Static("No fallbacks to review.", id="empty")
        yield Footer()

    async def on_mount(self) -> None:
        table = self.query_one(DataTable)
        for label in ("", "File", "Key", "Rule", "Current"):
            table.add_column(label, key=label or "mark")
        self.query_one("#hint").display = self._model is None
        await self._load()

    async def _load(self) -> None:
        """The record as it is now; the marks are cleared."""
        try:
            self._entries = (await self._mediator.send(ListFallbacksQuery(self._tree))).entries
        except REFUSALS as error:
            self.notify(error.message, severity="error")
            self._entries = ()
        self._marked.clear()
        table = self.query_one(DataTable)
        table.clear()
        for index, view in enumerate(self._entries):
            entry = view.entry
            place = f"{entry.file} [{entry.key}]" if entry.key else str(entry.file)
            rules = ", ".join(dict.fromkeys(problem.rule.value for problem in entry.problems))
            cells = (place, str(entry.path), rules, view.current or "")
            table.add_row("", *(escape(cell) for cell in cells), key=str(index))
        empty = not self._entries
        table.display = not empty
        self.query_one("#detail").display = not empty
        self.query_one("#empty").display = empty
        self._detail()
        self.refresh_bindings()

    def _highlighted(self) -> FallbackView | None:
        table = self.query_one(DataTable)
        if not self._entries or not 0 <= table.cursor_row < len(self._entries):
            return None
        return self._entries[table.cursor_row]

    def _chosen(self) -> list[FallbackView]:
        """The marked entries, else the highlighted one."""
        if self._marked:
            return [self._entries[index] for index in sorted(self._marked)]
        view = self._highlighted()
        return [view] if view is not None else []

    @on(DataTable.RowHighlighted)
    def _detail(self) -> None:
        view = self._highlighted()
        detail = self.query_one("#detail", Static)
        if view is None:
            detail.update("")
            return
        lines = [f"[b]Source[/]    {escape(view.source or STALE)}"]
        if view.entry.rejected is not None:
            lines.append(f"[b]Rejected[/]  {escape(view.entry.rejected)}")
        lines += [f"[b]Problem[/]   {escape(problem.message)}" for problem in view.entry.problems]
        detail.update("\n".join(lines))
        self.refresh_bindings()

    def check_action(self, action: str, parameters: tuple[object, ...]) -> bool | None:
        if action in ("mark", "accept"):
            return bool(self._entries)
        if action == "edit":
            view = self._highlighted()
            return None if view is None or view.stale else True
        if action == "retry":
            return None if self._model is None or not self._entries else True
        return True

    def action_mark(self) -> None:
        table = self.query_one(DataTable)
        index = table.cursor_row
        if not 0 <= index < len(self._entries):
            return
        self._marked.symmetric_difference_update({index})
        table.update_cell(str(index), "mark", "●" if index in self._marked else "")

    def action_edit(self) -> None:
        view = self._highlighted()
        if view is None or view.ref is None:
            return
        screen = EditScreen(self._mediator, self._tree, view.ref, view.current or "")
        self.app.push_screen(screen, self._edited)

    async def _edited(self, written: bool | None) -> None:
        if written:
            await self._load()

    @work(exclusive=True, group="review")
    async def action_retry(self) -> None:
        if self._model is None:
            return
        refs = tuple(view.ref for view in self._chosen() if view.ref is not None)
        if not refs:
            self.notify(f"Nothing to retry: {STALE}.", severity="warning")
            return
        self.notify(f"Translating {count(len(refs), 'message')} again…")
        try:
            receipt = await self._mediator.send(
                RetryFallbacksCommand(self._tree, self._model, refs, self._options)
            )
        except REFUSALS as error:
            self.notify(error.message, severity="error")
            return
        failed = [r for r in receipt.results if r.status == ResultStatus.FAILED]
        for result in failed:
            self.notify(f"{result.file} → {result.target}: {result.reason}", severity="error")
        await self._load()

    @work(exclusive=True, group="review")
    async def action_accept(self) -> None:
        entries = tuple(view.entry for view in self._chosen())
        if not entries:
            return
        try:
            await self._mediator.send(AcceptFallbacksCommand(self._tree, entries))
        except REFUSALS as error:
            self.notify(error.message, severity="error")
            return
        await self._load()

    def action_back(self) -> None:
        self.dismiss()


class EditScreen(ModalScreen[bool]):
    """A message's text, edited by hand: written when it keeps to the rules, else the problems
    are shown and the dialog stays open."""

    DEFAULT_CSS = """
    EditScreen { align: center middle; }
    EditScreen > Vertical {
        width: 80; height: auto; border: round $accent; padding: 1 2; background: $surface;
    }
    EditScreen #problems { color: $error; }
    """
    BINDINGS = [Binding("escape", "cancel", "Cancel")]

    def __init__(self, mediator: Mediator, tree: TreeRequest, ref: MessageRef, text: str) -> None:
        super().__init__()
        self._mediator = mediator
        self._tree = tree
        self._ref = ref
        self._text = text

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Static(escape(f"{self._ref.file} → {self._ref.target.value}: {self._ref.path}"))
            yield Input(self._text, id="text", compact=True)
            yield Static("", id="problems")

    @on(Input.Submitted, "#text")
    async def _submitted(self, event: Input.Submitted) -> None:
        problems = self.query_one("#problems", Static)
        try:
            result = await self._mediator.send(
                SetMessageCommand(self._tree, self._ref, event.value)
            )
        except REFUSALS as error:
            problems.update(escape(error.message))
            return
        if not result.written:
            problems.update(
                "\n".join(
                    escape(violation.message) for violation in errors(list(result.violations))
                )
            )
            return
        self.dismiss(True)

    def action_cancel(self) -> None:
        self.dismiss(False)
