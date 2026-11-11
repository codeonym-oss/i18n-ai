import dataclasses
from pathlib import Path

from mediary import Mediator
from rich.console import Console
from textual import events, on, work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Grid, Horizontal, Vertical, VerticalScroll
from textual.content import Content
from textual.reactive import reactive
from textual.widgets import Button, Checkbox, ContentSwitcher, Input, Label, Select, Static

from ...application.exports.locale import (
    GenerateLocalesCommand,
    ListFallbacksQuery,
    ListLocalesQuery,
    LocaleView,
    ScanLocaleTreeQuery,
    ScanReport,
)
from ...application.exports.provider import (
    GetProviderStatusQuery,
    InstallProviderCommand,
    ListModelsQuery,
    ListProvidersQuery,
    ProviderView,
    SetProviderKeyCommand,
)
from ...application.ports.locale import TreeRequest
from ...domain.exports.locale import LocaleCode, SourceLocaleUnknown
from ...domain.exports.provider import ModelSpec
from ...runtime.answers import Answers, save_answers
from ...runtime.config import GenerationConfig
from ..common.setup import (
    Choice,
    answers_of,
    command_line,
    generation_options,
    locale_choices,
    model_choices,
    output_choices,
    provider_choices,
    source_choices,
    within,
)
from .confirm import ConfirmScreen
from .kit.heat import percent
from .kit.shell import ShellScreen
from .kit.widgets import Card, Chip, LocaleCard, ModelCard
from .plan import PlanScreen, count
from .progress import TuiProgress
from .refusals import REFUSALS
from .run import RunScreen
from .trees import Trees

_NEEDED = "key needed"

# Each step: its name, its title, and the note under the title until the tree tells more
STEPS = {
    "tree": ("Tree", "Which tree?", "the tree, its source, where the targets go"),
    "targets": ("Targets", "Which locales?", "the locales to write"),
    "model": ("Model", "Which model?", "the provider, its model and its key"),
}
FILTERS = ("all", "tree", "rtl", "picked")
SHOWN = 24  # the most locale cards mounted at once
FIGURES = ("files", "locales", "messages")


class SetupScreen(ShellScreen[None]):
    """A generation set up in three steps: the tree, its source and where the targets go; the
    target locales, as cards; the provider, its model and key. A field waits until what it
    depends on is set; the run's panel says what is picked and how much the run covers."""

    DEFAULT_CSS = """
    SetupScreen #setup { height: 1fr; }
    SetupScreen #wizard-side { width: 1fr; }
    SetupScreen #this-run { width: 40; height: auto; margin-left: 1; margin-top: 1; }
    SetupScreen.-narrow #setup { layout: vertical; }
    SetupScreen.-narrow #this-run { width: 1fr; margin: 0; }
    SetupScreen.-narrow #figures { margin: 0; }
    SetupScreen.-narrow #run-model-card { display: none; }
    SetupScreen.-narrow .step-note { display: none; }
    SetupScreen #steps { height: 1; margin: 1 0; }
    SetupScreen.-narrow #steps { margin: 0 0 1 0; }
    SetupScreen .step { width: auto; padding: 0 1; color: $text-muted; }
    SetupScreen .step.-now { background: $border-blurred; color: $foreground; text-style: bold; }
    SetupScreen .step.-done { color: $success; }
    SetupScreen .step-line { width: auto; color: $border-strong; }
    SetupScreen #steps-gap { width: 1fr; }
    SetupScreen #continue { margin-right: 1; }
    SetupScreen #wizard { height: 1fr; }
    SetupScreen .step-head { width: 1fr; height: auto; margin-bottom: 1; }
    SetupScreen .step-title { text-style: bold; }
    SetupScreen .step-note { color: $text-muted; }
    SetupScreen #targets-head { height: auto; }
    SetupScreen #search-box { width: 36; height: 1; background: $surface; }
    SetupScreen #search-glyph { width: 3; padding-left: 1; color: $text-muted; }
    SetupScreen #search { width: 1fr; }
    SetupScreen #matches { width: auto; padding: 0 1; color: $text-muted; }
    SetupScreen #filters { height: 1; margin-bottom: 1; }
    SetupScreen .filter { width: auto; padding: 0 1; margin-right: 1; color: $text-muted; }
    SetupScreen .filter.-on { background: $border-blurred; color: $foreground; }
    SetupScreen #cards { grid-size: 4; grid-gutter: 0 1; grid-rows: 5; height: auto; }
    SetupScreen.-narrow #cards { grid-size: 2; }
    SetupScreen #more { color: $text-muted; margin-top: 1; }
    SetupScreen .row { height: auto; }
    SetupScreen .row > Label { width: 13; padding-left: 1; }
    SetupScreen .row > Vertical { height: auto; width: 1fr; }
    SetupScreen #model-card { margin-bottom: 1; padding: 0 1; border: round $border; }
    SetupScreen #figures { height: auto; margin-top: 1; }
    SetupScreen #picked { height: 1; }
    SetupScreen #picked > .chip { margin-right: 1; }
    SetupScreen #picked > .none { color: $text-muted; }
    SetupScreen .figure { width: 1fr; height: auto; background: $panel; margin-right: 1; }
    SetupScreen .figure-value { width: 1fr; text-align: center; text-style: bold; }
    SetupScreen .figure-label { width: 1fr; text-align: center; color: $text-muted; }
    SetupScreen #plan { color: $error; }
    SetupScreen #fallbacks { color: $warning; }
    """
    BINDINGS = [
        Binding("ctrl+r", "plan", "Plan"),
        Binding("escape", "back", "Back"),
        Binding("slash", "search", "Search"),
        Binding("v", "review", "Review"),
    ]
    SECTION = "run"

    def __init__(
        self,
        mediator: Mediator,
        console: Console,
        settings: GenerationConfig,
        progress: TuiProgress,
        project: Path,
        answers: Answers,
        trees: Trees,
        tree: str | None,
    ) -> None:
        super().__init__()
        self._mediator = mediator
        self._quiet = console
        self._settings = settings
        self._progress = progress
        self._project = project
        self._last = answers
        # The settings' model, else the last one, is the provider's and model's default
        self._defaults = dataclasses.replace(answers, model=settings.model or answers.model)
        self._shown = within(project)
        self._request: TreeRequest | None = None
        self._trees = trees
        self._tree = tree  # the tree it starts on
        self._preset_tree = trees.preset
        self._source = ""  # the tree's source locale, once scanned
        self._locales: tuple[LocaleView, ...] = ()
        self._targets: list[Choice] = []
        self._checked: set[str] = set()
        self._in_tree: set[str] = set()  # the targets the tree already has
        self._done: dict[str, int] = {}  # their share translated
        self._messages = 0  # in the source, what a new locale needs
        self._filter = "all"
        self._opened = False  # the first scan opens the step it leaves to fill
        self._providers: dict[str, ProviderView] = {}
        self._recommended: set[str] = set()  # the provider's recommended models
        self._keyed: set[str] = set()  # the providers given a key here
        self.fallbacks = 0  # recorded beside the tree's targets

    step = reactive("tree", init=False)

    def body(self) -> ComposeResult:
        with Horizontal(id="setup"):
            with Vertical(id="wizard-side"):
                with Horizontal(id="steps"):
                    for number, name in enumerate(STEPS):
                        if number:
                            yield Static("──", classes="step-line")
                        yield Static("", id=f"step-{name}", classes="step")
                    yield Static("", id="steps-gap")
                    yield Button("Continue", id="continue", compact=True)
                    yield Button("Plan ⌃R", id="next", variant="primary", compact=True)
                with ContentSwitcher(id="wizard", initial="tree-step"):
                    with VerticalScroll(id="tree-step"):
                        yield _title("tree")
                        yield _row(
                            "Locale tree",
                            Select[str]([], id="tree", prompt="Pick a tree", compact=True),
                            Input(
                                placeholder="no tree found: its path, then Enter",
                                id="tree-path",
                                compact=True,
                            ),
                        )
                        yield _row(
                            "Source",
                            Select[str]([], id="source", prompt="Pick the source", compact=True),
                            id="source-row",
                        )
                        yield _row(
                            "Output",
                            Select[str](
                                [], id="output", prompt="Where they go", compact=True, disabled=True
                            ),
                        )
                    with Vertical(id="targets-step"):
                        with Horizontal(id="targets-head"):
                            yield _title("targets")
                            with Horizontal(id="search-box"):
                                yield Static("⌕", id="search-glyph")
                                yield Input(
                                    placeholder="search…", id="search", compact=True, disabled=True
                                )
                                yield Static("", id="matches")
                        with Horizontal(id="filters"):
                            for name in FILTERS:
                                yield Static("", id=f"filter-{name}", classes="filter")
                        with VerticalScroll(id="cards-scroll"):
                            yield Grid(id="cards")
                            yield Static("", id="more")
                    with VerticalScroll(id="model-step"):
                        yield _title("model")
                        yield ModelCard(id="model-card")
                        yield _row(
                            "Provider", Select[str]([], id="provider", prompt="Pick", compact=True)
                        )
                        yield _row(
                            "Model",
                            Select[str](
                                [], id="model", prompt="Pick a model", compact=True, disabled=True
                            ),
                        )
                        yield _row(
                            "Key",
                            Static("", id="key-state"),
                            Input(
                                placeholder="the key (hidden)",
                                password=True,
                                id="key",
                                compact=True,
                            ),
                            Checkbox("Save it in the system keyring", id="save", compact=True),
                            id="key-row",
                        )
            with Vertical(id="this-run"):
                with Card(title="THIS RUN", id="run-card"):
                    yield Horizontal(id="picked")
                    with Horizontal(id="figures"):
                        for name in FIGURES:
                            yield Vertical(
                                Static("–", classes="figure-value"),
                                Static(name, classes="figure-label"),
                                id=name,
                                classes="figure",
                            )
                    yield Static("", id="plan")
                    yield Static("", id="fallbacks")
                yield Card(ModelCard(id="run-model"), title="MODEL", id="run-model-card")

    async def on_mount(self) -> None:
        self.query_one("#source-row").display = False
        self.query_one("#tree-path").display = False
        self.query_one("#fallbacks").display = False
        self.query_one("#more").display = False
        self._show_key(None)
        await self._show_picks()
        self.watch_step()
        if not self._trees.choices:
            self.query_one("#tree").display = False
            self.query_one("#tree-path").display = True
        _fill(self.query_one("#tree", Select), list(self._trees.choices), self._tree)
        try:
            # The providers, those ready first
            providers = await self._mediator.send(ListProvidersQuery())
            self._providers = {provider.name: provider for provider in providers}
            choices, default = provider_choices(providers, self._defaults)
            _fill(self.query_one("#provider", Select), choices, default)
            self._locales = await self._mediator.send(ListLocalesQuery())
        except REFUSALS as error:
            self.notify(error.message, severity="error")

    @on(Select.Changed, "#tree")
    async def _tree_picked(self, event: Select.Changed) -> None:
        self._request = None
        if not isinstance(event.value, str):
            await self._tree_ready(False)
            return
        picked = Path(event.value)
        # The preset's format and syntax are for its own locales
        preset = self._preset_tree
        base = preset if event.value == self._shown(preset.path) else TreeRequest(Path())
        self.query_one("#source-row").display = False
        await self._scan(dataclasses.replace(base, path=picked, source=None))

    @on(Input.Submitted, "#tree-path")
    async def _tree_typed(self, event: Input.Submitted) -> None:
        if event.value.strip():
            self.query_one("#source-row").display = False
            await self._scan(TreeRequest(Path(event.value.strip())))

    @on(Select.Changed, "#source")
    async def _source_picked(self, event: Select.Changed) -> None:
        if isinstance(event.value, str) and self._request is not None:
            await self._scan(dataclasses.replace(self._request, source=LocaleCode(event.value)))

    async def _scan(self, request: TreeRequest) -> None:
        """The tree's source and locales: the source asked when the tree cannot tell it."""
        self._request = request
        try:
            found = await self._mediator.send(ScanLocaleTreeQuery(request))
        except SourceLocaleUnknown as error:
            if request.source is not None:
                self.notify(error.message, severity="error")
                await self._tree_ready(False)
                return
            locales = error.details["found"]
            source = self._last.source if self._last.source in locales else None
            self.query_one("#source-row").display = True
            _fill(self.query_one("#source", Select), source_choices(locales), source)
            await self._tree_ready(False)
            self._opened = True
            return
        except REFUSALS as error:
            self.notify(error.message, severity="error")
            await self._tree_ready(False)
            self._opened = True
            return
        self._source = found.source
        self._in_tree = set(found.existing) - {found.source}
        self._messages = sum(file.messages for file in found.qualified)
        self._done = await self._coverage(request, found)
        self._targets, self._checked = locale_choices(
            self._locales, found.existing, found.source, self._last
        )
        # The tree's locales first, then those picked last time
        self._targets.sort(
            key=lambda choice: (
                choice.value not in self._in_tree,
                choice.value not in self._checked,
            )
        )
        self.query_one("#tree-note", Static).update(
            f"{self._shown(found.root)} · {found.layout}, {found.format}"
        )
        self.query_one("#targets-note", Static).update(
            f"From {found.source} · {len(self._locales)} CLDR locales · the ones in the tree first"
        )
        await self._show_targets()
        choices, default = output_choices(found.root, self._last, self._shown)
        _fill(self.query_one("#output", Select), choices, default or "")
        await self._tree_ready(True)
        await self._count_fallbacks()
        if not self._opened:
            self._opened = True
            self.step = "targets"

    async def _coverage(self, request: TreeRequest, found: ScanReport) -> dict[str, int]:
        """Each locale in the tree: its share of the source's messages translated."""
        existing = tuple(LocaleCode(code) for code in found.existing if code != found.source)
        if not existing:
            return {}
        try:
            report = await self._mediator.send(ScanLocaleTreeQuery(request, existing))
        except REFUSALS:
            return {}
        shares = {}
        for target in report.targets:
            done = sum(file.reusable for file in target.files)
            shares[target.locale] = percent(done, done + target.to_translate)
        return shares

    async def _tree_ready(self, ready: bool) -> None:
        for selector in ("#search", "#output"):
            self.query_one(selector).disabled = not ready
        if not ready:
            self._source = ""
            self._targets, self._checked, self._in_tree = [], set(), set()
            await self._show_targets()
            self._show_fallbacks(0)
        self._show_chips()
        self._plan()

    async def on_screen_resume(self) -> None:
        # Back from a run or a review, the record may have changed
        if self._source:
            await self._count_fallbacks()

    async def _count_fallbacks(self) -> None:
        if self._request is None:
            return
        try:
            view = await self._mediator.send(ListFallbacksQuery(self._request))
        except REFUSALS:
            view = None
        self._show_fallbacks(len(view.entries) if view is not None else 0)

    def _show_fallbacks(self, number: int) -> None:
        self.fallbacks = number
        line = self.query_one("#fallbacks", Static)
        line.display = bool(number)
        line.update(f"{count(number, 'fallback')} recorded · v to review")
        self.refresh_bindings()

    def check_action(self, action: str, parameters: tuple[object, ...]) -> bool | None:
        return bool(self.fallbacks) if action == "review" else True

    def watch_step(self) -> None:
        """The step shown, named in the command bar and the status line, its first field
        focused."""
        self.query_one("#wizard", ContentSwitcher).current = f"{self.step}-step"
        self.query_one("#continue").display = self.step != "model"
        label = STEPS[self.step][0]
        crumb = Content.from_markup(f"[$text-muted]New run /[/] [b]{label}[/b]")
        self.query_one("#crumb", Static).update(crumb)
        self.query_one("#status-tree", Static).update(self.status_tree())
        self._show_chips()
        self.call_after_refresh(self._focus_step)

    def status_tree(self) -> str:
        number = list(STEPS).index(self.step) + 1
        return f"step {number} of {len(STEPS)} · {self.step}  ·  {super().status_tree()}"

    def _focus_step(self) -> None:
        """The step's first card, else its first field."""
        pane = self.query_one(f"#{self.step}-step")
        fields = [*pane.query(LocaleCard), *pane.query("*")]
        first = next((field for field in fields if field.focusable), None)
        if first is not None:
            first.focus()

    def _show_chips(self) -> None:
        """Each step's chip: ✓ once its fields are filled, raised when it shows."""
        filled = {
            "tree": bool(self._source),
            "targets": bool(self._picked_targets()),
            "model": self._model() is not None and self._key_state(self._provider()) != _NEEDED,
        }
        for number, (name, (label, _, _)) in enumerate(STEPS.items(), 1):
            chip = self.query_one(f"#step-{name}", Static)
            now, done = name == self.step, filled[name]
            if now:
                chip.update(f"● {number} {label}")
            else:
                chip.update(f"✓ {label}" if done else f"{number} {label}")
            chip.set_class(now, "-now")
            chip.set_class(done and not now, "-done")

    @on(events.Click)
    async def _clicked(self, event: events.Click) -> None:
        """A step's chip opens it; a filter's chip filters the cards."""
        name = (event.widget.id or "") if event.widget is not None else ""
        if name.startswith("step-"):
            self.step = name.removeprefix("step-")
        elif name.startswith("filter-"):
            self._filter = name.removeprefix("filter-")
            await self._show_targets()

    @on(Button.Pressed, "#continue")
    def _continue(self) -> None:
        self._move(1)

    def action_back(self) -> None:
        self._move(-1)

    def _move(self, by: int) -> None:
        """The step `by` steps on, kept within the first and the last."""
        names = list(STEPS)
        self.step = names[min(max(names.index(self.step) + by, 0), len(names) - 1)]

    def action_search(self) -> None:
        self.step = "targets"
        self.call_after_refresh(self.query_one("#search", Input).focus)

    def _model(self) -> ModelSpec | None:
        """The form's model, once its provider and model are picked."""
        provider = self.query_one("#provider", Select).value
        model = self.query_one("#model", Select).value
        if isinstance(provider, str) and isinstance(model, str):
            return ModelSpec(f"{provider}:{model}")
        return None

    def action_review(self) -> None:
        if self._request is not None and self.fallbacks:
            self.shell.open_review(self._request, self._model())

    @on(Input.Changed, "#search")
    async def _search(self) -> None:
        await self._show_targets()

    async def _show_targets(self) -> None:
        """The cards of the targets matching the search and the filter, picked as they were;
        past `SHOWN`, how many more match."""
        words = self.query_one("#search", Input).value.strip().lower()
        matching = [
            choice
            for choice in self._targets
            if words in choice.title.lower() and self._kept(choice.value)
        ]
        cards = self.query_one("#cards", Grid)
        await cards.remove_children()
        await cards.mount_all(self._card(choice.value) for choice in matching[:SHOWN])
        more = self.query_one("#more", Static)
        more.display = len(matching) > SHOWN
        more.update(f"+{len(matching) - SHOWN} more · type to narrow")
        self.query_one("#matches", Static).update(f"{len(matching)} match" if words else "")
        await self._show_picks()

    def _kept(self, code: str) -> bool:
        """Whether the filter keeps the locale."""
        if self._filter == "tree":
            return code in self._in_tree
        if self._filter == "rtl":
            return LocaleCode(code).direction == "rtl"
        if self._filter == "picked":
            return code in self._checked
        return True

    def _card(self, code: str) -> LocaleCard:
        locale = LocaleCode(code)
        if code in self._in_tree:
            state = f"in tree · {self._done.get(code, 0)}% done"
        else:
            state = f"new · {count(self._messages, 'message')}"
        in_tree, picked = code in self._in_tree, code in self._checked
        return LocaleCard(code, locale.display_name, locale.direction, state, in_tree, picked)

    async def _show_picks(self) -> None:
        """The filters' counts, and the picked locales as chips in the run's panel."""
        picked = len(self._picked_targets())
        labels = {
            "all": "All",
            "tree": f"In the tree · {len(self._in_tree)}",
            "rtl": "Right to left",
            "picked": f"Picked · {picked}",
        }
        for name, label in labels.items():
            chip = self.query_one(f"#filter-{name}", Static)
            chip.update(label)
            chip.set_class(name == self._filter, "-on")
        chips = self.query_one("#picked", Horizontal)
        await chips.remove_children()
        codes = [target.value for target in self._picked_targets()]
        await chips.mount_all(
            [Chip(code, "×", "primary") for code in codes]
            or [Static("no target yet", classes="none")]
        )

    @on(LocaleCard.Toggled)
    async def _toggled(self, event: LocaleCard.Toggled) -> None:
        if event.card.picked:
            self._checked.add(event.card.code)
        else:
            self._checked.discard(event.card.code)
        await self._show_picks()
        self._show_chips()
        self._plan()

    @on(Select.Changed, "#output")
    def _output_picked(self, event: Select.Changed) -> None:
        if self._request is not None and isinstance(event.value, str):
            output = Path(event.value) if event.value else None
            self._request = dataclasses.replace(self._request, output=output)
            self._plan()

    def _picked_targets(self) -> tuple[LocaleCode, ...]:
        return tuple(
            LocaleCode(choice.value) for choice in self._targets if choice.value in self._checked
        )

    @work(exclusive=True, group="plan")
    async def _plan(self) -> None:
        """How many files, locales and messages the run covers."""
        plan = self.query_one("#plan", Static)
        plan.display = False
        targets = self._picked_targets()
        figures: tuple[object, ...] = ("–",) * len(FIGURES)
        if self._request is not None and self._source and targets:
            try:
                report = await self._mediator.send(ScanLocaleTreeQuery(self._request, targets))
            except REFUSALS as error:
                plan.update(error.message)
                plan.display = True
            else:
                figures = (len(report.qualified), len(report.targets), report.to_translate)
        for name, figure in zip(FIGURES, figures, strict=True):
            self.query_one(f"#{name} .figure-value", Static).update(str(figure))

    @on(Select.Changed, "#provider")
    async def _provider_picked(self, event: Select.Changed) -> None:
        models = self.query_one("#model", Select)
        provider = self._providers.get(event.value) if isinstance(event.value, str) else None
        self._show_key(provider)
        # Another provider's models are not this one's
        models.set_options([])
        models.disabled = True
        self._show_model()
        if provider is None:
            return
        await self._list_models(provider.name)

    @on(Select.Changed, "#model")
    def _model_picked(self) -> None:
        self._show_model()

    def _provider(self) -> ProviderView | None:
        provider = self.query_one("#provider", Select).value
        return self._providers.get(provider) if isinstance(provider, str) else None

    def _show_model(self) -> None:
        """The model cards, in the Model step and the run's panel."""
        provider = self._provider()
        model = self.query_one("#model", Select).value
        picked = model if isinstance(model, str) else None
        key = self._key_state(provider)
        name = provider.name if provider is not None else None
        needs_key = key == _NEEDED
        for card in self.query(ModelCard):
            card.show(name, picked, key, needs_key, picked in self._recommended)
        self._show_chips()

    async def _list_models(self, provider: str) -> None:
        models = self.query_one("#model", Select)
        try:
            listing = await self._mediator.send(ListModelsQuery(provider))
        except REFUSALS as error:
            self.notify(error.message, severity="error")
            return
        if listing.problem:
            self.notify(f"{listing.problem}; showing the recommended models.")
        self._recommended = {model.id for model in listing.models if model.recommended}
        choices, default = model_choices(listing, provider, self._defaults)
        _fill(models, choices, default)
        models.disabled = False
        self._show_model()

    def _key_state(self, provider: ProviderView | None) -> str:
        """What the provider's key is: none needed, needed, or set and from where."""
        if provider is None:
            return ""
        if provider.key is None:
            return "none needed"
        if not provider.key_set and provider.name not in self._keyed:
            return _NEEDED
        return f"✓ set ({provider.key_source or 'for this run'})"

    def _show_key(self, provider: ProviderView | None) -> None:
        """The key: said when it is set, else asked."""
        key = self._key_state(provider)
        missing = key == _NEEDED
        state = self.query_one("#key-state", Static)
        state.display = not missing
        self.query_one("#key").display = missing
        self.query_one("#save").display = missing
        if provider is None:
            state.update("[$text-muted]the provider's[/]")
        elif provider.key is None:
            state.update(f"[$text-muted]{key}[/]")
        elif not missing:
            state.update(f"[$success]✓[/] set ({provider.key_source or 'for this run'})")

    @on(Input.Submitted, "#key")
    async def _key_given(self) -> None:
        await self._give_key()

    async def _give_key(self) -> None:
        """The key typed, used for this run, and saved in the keyring when the box says so."""
        provider = self.query_one("#provider", Select).value
        key = self.query_one("#key", Input)
        if not isinstance(provider, str) or not key.value:
            return
        save = self.query_one("#save", Checkbox).value
        try:
            receipt = await self._mediator.send(SetProviderKeyCommand(provider, key.value, save))
        except REFUSALS as error:
            self.notify(error.message, severity="error")
            return
        if receipt.saved:
            self.notify(f"{receipt.variable} saved in the system keyring.")
        elif receipt.problem:
            self.notify(
                f"{receipt.problem}: the key is used for this run only.", severity="warning"
            )
        key.value = ""
        self._keyed.add(provider)
        self._show_key(self._providers[provider])
        self._show_model()
        await self._list_models(provider)

    @on(Button.Pressed, "#next")
    def action_plan(self) -> None:
        self._run()

    @work(exclusive=True, group="run")
    async def _run(self) -> None:
        """The plan, then the run. A missing provider package is asked about first, before it
        is installed; the plan's Run is the go-ahead."""
        request, targets, model = self._request, self._picked_targets(), self._model()
        if request is None or not self._source:
            self.step = "tree"
            self.notify("Pick a locale tree first.", severity="warning")
            return
        if not targets:
            self.step = "targets"
            self.notify("Pick a target first.", severity="warning")
            return
        if model is None:
            self.step = "model"
            self.notify("Pick a model first.", severity="warning")
            return
        spec = str(model)
        try:
            if self.query_one("#key", Input).value:
                await self._give_key()
            status = await self._mediator.send(GetProviderStatusQuery(ModelSpec(spec)))
            if not status.installed:
                question = (
                    f"The {status.provider} provider needs {status.package}, not installed. "
                    "Install it now?"
                )
                await self._in_run()
                if not await self.app.push_screen_wait(ConfirmScreen(question)):
                    return
                self.notify(f"Installing {status.package}…")
                installed = await self._mediator.send(InstallProviderCommand(status.provider))
                self.notify(f"{installed.package} installed.")
            save_answers(self._project, answers_of(request, targets, spec, self._shown))
            report = await self._mediator.send(ScanLocaleTreeQuery(request, targets))
        except REFUSALS as error:
            self.notify(error.message, severity="error")
            return
        try:
            fallbacks = (await self._mediator.send(ListFallbacksQuery(request))).entries
        except REFUSALS:
            fallbacks = ()  # the record unread: the plan shows none, the run goes on
        options = generation_options(self._settings)
        await self._in_run()
        plan = await self.app.push_screen_wait(PlanScreen(report, fallbacks, options.batch_size))
        if plan is None:
            return
        request = dataclasses.replace(request, exclude=request.exclude + plan.exclude)

        screen = RunScreen(report, plan, self._shown(request.path))
        await self._in_run()
        await self.app.push_screen(screen)
        self._progress.target = screen
        command = GenerateLocalesCommand(
            request,
            plan.targets,
            ModelSpec(spec),
            options,
            skip=plan.skip,
        )
        try:
            receipt = await self._mediator.send(command)
        except REFUSALS as error:
            screen.stopped(error.message)
            return
        finally:
            self._progress.target = None
        output = self._shown(request.output) if request.output else None
        flags = [word for pattern in plan.exclude for word in ("--exclude", pattern)]
        again = command_line(
            self._shown(request.path), plan.targets, spec, request.source, output, flags
        )
        one = len(plan.skip) == 1
        note = (
            f"{count(len(plan.skip), 'single cell')} {'was' if one else 'were'} off; "
            f"this command runs {'it' if one else 'them'} too."
        )
        try:
            left = (await self._mediator.send(ListFallbacksQuery(request))).entries
        except REFUSALS:
            left = ()
        review = (lambda: self.shell.open_review(request, ModelSpec(spec))) if left else None
        screen.show_receipt(receipt, again, note if plan.skip else None, review)

    async def _in_run(self) -> None:
        """The Run section shown, for a screen pushed on it: another section may have been
        picked while the worker waited."""
        if self.app.current_mode != "run":
            await self.app.switch_mode("run")


def _title(step: str) -> Vertical:
    """A step's title, and the note under it."""
    _, title, note = STEPS[step]
    return Vertical(
        Static(title, classes="step-title"),
        Static(note, id=f"{step}-note", classes="step-note", markup=False),
        classes="step-head",
    )


def _row(
    label: str,
    *fields: Static | Input | Select[str] | Checkbox,
    id: str | None = None,
) -> Horizontal:
    return Horizontal(Label(label), Vertical(*fields), classes="row", id=id)


def _fill(select: Select[str], choices: list[Choice], default: str | None) -> None:
    """`select`'s options, and the default when it is one of them."""
    select.set_options((choice.title, choice.value) for choice in choices)
    if default is not None and any(choice.value == default for choice in choices):
        select.value = default
