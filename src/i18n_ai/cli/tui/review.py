from mediary import Mediator
from rich.markup import escape
from textual import on, work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Grid, Horizontal, Vertical
from textual.widgets import DataTable, Input, Static

from ...application.exports.locale import (
    AcceptFallbacksCommand,
    FallbackView,
    GenerationOptions,
    ListFallbacksQuery,
    ResultStatus,
    RetryFallbacksCommand,
    SetMessageCommand,
)
from ...application.ports.locale import TreeRequest
from ...domain.exports.locale import errors
from ...domain.exports.provider import ModelSpec
from ..common.setup import within
from .kit.shell import ShellScreen
from .kit.widgets import Card, Chip
from .plan import count
from .refusals import REFUSALS

STALE = "no longer in the source"


class ReviewScreen(ShellScreen[None]):
    """The fallbacks a tree's runs left, listed; beside the list, the one under the cursor: its
    source, the model's last rejected translation with the rules it broke, its text in the file
    now, an editor to fix it, and the same message in the tree's other locales. A fix is checked
    when it is saved, and written only when it keeps to the rules; the marked ones (or the
    highlighted one) are translated again with the setup's model, or accepted as they are. An
    entry whose message is gone from the source can only be accepted."""

    BINDINGS = [
        Binding("space", "mark", "Mark"),
        Binding("e", "edit", "Edit"),
        Binding("r", "retry", "Retry"),
        Binding("a", "accept", "Accept"),
        Binding("b,escape", "back", "Back"),
    ]
    SECTION = "review"

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

    def body(self) -> ComposeResult:
        with Horizontal(id="review"):
            yield DataTable[str](id="fallbacks", cursor_type="row")
            with Vertical(id="focus"):
                with Horizontal(id="head"):
                    yield Static("", id="where", markup=False)
                    yield Chip("✕", "", "warning", id="rule")
                    yield Static("", id="position")
                with Grid(id="cards"):
                    yield _Compared("Source", "SOURCE", "source")
                    yield _Compared("Last attempt", "MODEL", "model")
                    yield _Compared("In the file", "NOW", "now")
                with Card(title="Your translation", id="editor"):
                    yield Input(id="text", compact=True)
                    yield Static("", id="check", markup=False)
                yield Static("Pick a model in the setup to retry.", id="hint")
            with Card(title="The same key elsewhere", id="elsewhere"):
                yield Static("", id="elsewhere-text")
        yield Static("No fallbacks to review.", id="empty")

    def status_tree(self) -> str:
        return within(self.shell.project)(self._tree.path)

    async def on_mount(self) -> None:
        table = self.query_one(DataTable)
        for label in ("", "File", "Key", "Rule"):
            table.add_column(label, key=label or "mark", width=1 if not label else None)
        self.query_one("#hint").display = self._model is None
        await self._load()

    async def _load(self, row: int = 0) -> None:
        """The record as it is now, the cursor on `row` or the last; the marks are cleared."""
        try:
            self._entries = (await self._mediator.send(ListFallbacksQuery(self._tree))).entries
        except REFUSALS as error:
            self.notify(error.message, severity="error")
            self._entries = ()
        self._marked.clear()
        if self.status_tree() == self.shell.locale_tree:
            self.shell.fallbacks = len(self._entries)  # the sidebar's count is of that tree
        table = self.query_one(DataTable)
        table.clear()
        for index, view in enumerate(self._entries):
            entry = view.entry
            cells = (_place(view), str(entry.path), _rules(view))
            table.add_row("", *(escape(cell) for cell in cells), key=str(index))
        empty = not self._entries
        self.query_one("#review").display = not empty
        self.query_one("#empty").display = empty
        if empty:
            self.set_focus(None)
        else:
            table.move_cursor(row=min(row, len(self._entries) - 1))
        self._detail()

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
        """The highlighted fallback beside the list."""
        view = self._highlighted()
        if view is None:
            return
        entry = view.entry
        self.query_one("#where", Static).update(f"{_place(view)} · {entry.path}")
        self.query_one("#rule", Chip).update(f"✕ {_rules(view)}")
        self._position()
        self.query_one("#source", _Compared).show(view.source or STALE)
        problems = [problem.message for problem in entry.problems]
        self.query_one("#model", _Compared).show(entry.rejected or "no translation", problems)
        self.query_one("#now", _Compared).show(view.current or "—")
        text = self.query_one("#text", Input)
        text.value = view.current or ""
        text.disabled = view.stale
        hint = f"can only be accepted: {STALE}" if view.stale else "enter checks and saves"
        self._check(f"✕ {_rules(view)} · {hint}", refused=False)
        lines = [f"[b]{code.value}[/b]  {escape(t) if t else '—'}" for code, t in view.elsewhere]
        self.query_one("#elsewhere-text", Static).update(
            "\n".join(lines) or "[$text-muted]no other locale[/]"
        )
        self.refresh_bindings()

    def _position(self) -> None:
        table = self.query_one(DataTable)
        parts = [f"{table.cursor_row + 1} of {len(self._entries)}"]
        if self._marked:
            parts.append(f"{len(self._marked)} marked")
        stale = sum(view.stale for view in self._entries)
        if stale:
            parts.append(f"{stale} stale")
        self.query_one("#position", Static).update(" · ".join(parts))

    def _check(self, line: str, refused: bool) -> None:
        check = self.query_one("#check", Static)
        check.update(line)
        check.set_class(refused, "-refused")

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
        self._position()

    def action_edit(self) -> None:
        self.query_one("#text", Input).focus()

    @on(Input.Submitted, "#text")
    async def _save(self, event: Input.Submitted) -> None:
        """The text checked and, kept to the rules, written; the next fallback comes up."""
        view = self._highlighted()
        if view is None or view.ref is None:
            return
        try:
            result = await self._mediator.send(SetMessageCommand(self._tree, view.ref, event.value))
        except REFUSALS as error:
            self._check(error.message, refused=True)
            return
        if not result.written:
            violations = errors(list(result.violations))
            self._check("\n".join(f"✕ {v.message}" for v in violations), refused=True)
            return
        await self._load(self.query_one(DataTable).cursor_row)

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
        await self._load(self.query_one(DataTable).cursor_row)

    def action_back(self) -> None:
        """Out of the editor to the list; from the list, back where the review came from."""
        if self.query_one("#text", Input).has_focus:
            self.query_one(DataTable).focus()
            return
        self.shell.leave_review()


class _Compared(Card):
    """A text to compare, in a card titled by what it is; when narrow, one line, its label
    before it."""

    def __init__(self, title: str, label: str, id: str) -> None:
        super().__init__(title=title, id=id)
        self._label = label

    def compose(self) -> ComposeResult:
        with Horizontal(classes="compared"):
            yield Static(self._label, classes="label")
            with Vertical(classes="compared-text"):
                yield Static("", classes="text", markup=False)
                yield Static("", classes="problem", markup=False)

    def show(self, text: str, problems: list[str] | None = None) -> None:
        self.query_one(".text", Static).update(text)
        problem = self.query_one(".problem", Static)
        problem.update("\n".join(f"✕ {line}" for line in problems or ()))
        problem.set_class(not problems, "-none")


def _place(view: FallbackView) -> str:
    """The target file the entry is in, and its key in a bundle."""
    entry = view.entry
    return f"{entry.file} [{entry.key}]" if entry.key else str(entry.file)


def _rules(view: FallbackView) -> str:
    return ", ".join(dict.fromkeys(problem.rule.value for problem in view.entry.problems))
