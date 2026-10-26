import dataclasses
from pathlib import Path

from mediary import Mediator
from rich.console import Console
from textual import on, work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import (
    Button,
    Checkbox,
    Footer,
    Header,
    Input,
    Label,
    Select,
    SelectionList,
    Static,
)

from ...application.contract import ApplicationException
from ...application.exports.locale import (
    DetectLocaleTreesQuery,
    GenerateLocalesCommand,
    ListLocalesQuery,
    LocaleView,
    ScanLocaleTreeQuery,
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
from ...di import InfraException
from ...domain.contract import DomainException
from ...domain.exports.locale import LocaleCode, SourceLocaleUnknown
from ...domain.exports.provider import ModelSpec
from ...runtime.answers import Answers, save_answers
from ...runtime.config import GenerationConfig
from ..common import tree_request, with_preset
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
    tree_choices,
    within,
)
from .confirm import ConfirmScreen
from .progress import TuiProgress
from .run import RunScreen

# What the mediator refuses with: shown, and the form stays as it was.
REFUSALS = (DomainException, ApplicationException, InfraException)


class SetupScreen(Screen[None]):
    """A generation set up as one form: the tree, its source and targets, where they go; the
    provider, its model and key. A field waits until what it depends on is set; the line beside
    Run says how many files and locales the run covers."""

    DEFAULT_CSS = """
    SetupScreen #form { padding: 0 1; }
    SetupScreen .group { text-style: bold; color: $accent; margin-top: 1; }
    SetupScreen .row { height: auto; }
    SetupScreen .row > Label { width: 13; padding-left: 1; }
    SetupScreen .row > Vertical { height: auto; width: 1fr; }
    SetupScreen #targets { height: auto; max-height: 6; }
    SetupScreen #go { height: auto; margin-top: 1; }
    SetupScreen #plan { padding-left: 2; color: $text-muted; }
    """
    BINDINGS = [Binding("ctrl+r", "run", "Run")]

    def __init__(
        self,
        mediator: Mediator,
        console: Console,
        settings: GenerationConfig,
        progress: TuiProgress,
        project: Path,
        answers: Answers,
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
        self._preset_tree = TreeRequest(Path())  # with the project's preset, once found
        self._source = ""  # the tree's source locale, once scanned
        self._locales: tuple[LocaleView, ...] = ()
        self._targets: list[Choice] = []
        self._checked: set[str] = set()
        self._providers: dict[str, ProviderView] = {}
        self._keyed: set[str] = set()  # the providers given a key here

    def compose(self) -> ComposeResult:
        yield Header()
        with VerticalScroll(id="form"):
            yield Label("Tree", classes="group")
            yield _row(
                "Locale tree",
                Select[str]([], id="tree", prompt="Pick a tree", compact=True),
                Input(
                    placeholder="no tree found: its path, then Enter", id="tree-path", compact=True
                ),
            )
            yield _row(
                "Source",
                Select[str]([], id="source", prompt="Pick the source", compact=True),
                id="source-row",
            )
            yield _row(
                "Targets",
                Input(placeholder="search…", id="search", compact=True, disabled=True),
                SelectionList[str](id="targets", compact=True, disabled=True),
            )
            yield _row(
                "Output",
                Select[str]([], id="output", prompt="Where they go", compact=True, disabled=True),
            )
            yield Label("Model", classes="group")
            yield _row("Provider", Select[str]([], id="provider", prompt="Pick", compact=True))
            yield _row(
                "Model",
                Select[str]([], id="model", prompt="Pick a model", compact=True, disabled=True),
            )
            yield _row(
                "Key",
                Static("", id="key-state"),
                Input(placeholder="the key (hidden)", password=True, id="key", compact=True),
                Checkbox("Save it in the system keyring", id="save", compact=True),
                id="key-row",
            )
            with Horizontal(id="go"):
                yield Button("Run", id="run", variant="primary", compact=True)
                yield Static("", id="plan")
        yield Footer()

    async def on_mount(self) -> None:
        self.query_one("#source-row").display = False
        self.query_one("#tree-path").display = False
        self._show_key(None)
        try:
            # The project's preset and trees, its first
            base = tree_request(Path(), None, None, None, None)
            self._preset_tree, match = await with_preset(
                self._mediator, self._quiet, base, None, given=False
            )
            if match is not None:
                self.app.sub_title = f"{match.preset.name} preset"
            candidates = await self._mediator.send(DetectLocaleTreesQuery(self._project))
            choices, default = tree_choices(candidates, match, self._last, self._shown)
            if not choices:
                self.query_one("#tree").display = False
                self.query_one("#tree-path").display = True
            _fill(self.query_one("#tree", Select), choices, default)

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
            self._tree_ready(False)
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
                self._tree_ready(False)
                return
            locales = error.details["found"]
            source = self._last.source if self._last.source in locales else None
            self.query_one("#source-row").display = True
            _fill(self.query_one("#source", Select), source_choices(locales), source)
            self._tree_ready(False)
            return
        except REFUSALS as error:
            self.notify(error.message, severity="error")
            self._tree_ready(False)
            return
        self._source = found.source
        self._targets, self._checked = locale_choices(
            self._locales, found.existing, found.source, self._last
        )
        self._show_targets()
        choices, default = output_choices(found.root, self._last, self._shown)
        _fill(self.query_one("#output", Select), choices, default or "")
        self._tree_ready(True)

    def _tree_ready(self, ready: bool) -> None:
        for selector in ("#search", "#targets", "#output"):
            self.query_one(selector).disabled = not ready
        if not ready:
            self._targets, self._checked = [], set()
            self._show_targets()
        self._plan()

    @on(Input.Changed, "#search")
    def _search(self) -> None:
        self._show_targets()

    def _show_targets(self) -> None:
        """The targets matching the search, checked as they were."""
        words = self.query_one("#search", Input).value.strip().lower()
        shown = [choice for choice in self._targets if words in choice.title.lower()]
        targets: SelectionList[str] = self.query_one("#targets", SelectionList)
        with targets.prevent(SelectionList.SelectedChanged):
            targets.clear_options()
            targets.add_options(
                (choice.title, choice.value, choice.value in self._checked) for choice in shown
            )

    @on(SelectionList.SelectedChanged, "#targets")
    def _targets_picked(self, event: SelectionList.SelectedChanged[str]) -> None:
        listed = {
            str(event.selection_list.get_option_at_index(index).value)
            for index in range(event.selection_list.option_count)
        }
        self._checked = (self._checked - listed) | set(event.selection_list.selected)
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
        """How many files and locales the run covers."""
        plan = self.query_one("#plan", Static)
        targets = self._picked_targets()
        if self._request is None or not self._source or not targets:
            plan.update("")
            return
        try:
            report = await self._mediator.send(ScanLocaleTreeQuery(self._request, targets))
        except REFUSALS as error:
            plan.update(error.message)
            return
        plan.update(
            f"{_count(len(report.qualified), 'file')} · {_count(len(report.targets), 'locale')}"
        )

    @on(Select.Changed, "#provider")
    async def _provider_picked(self, event: Select.Changed) -> None:
        models = self.query_one("#model", Select)
        provider = self._providers.get(event.value) if isinstance(event.value, str) else None
        self._show_key(provider)
        # Another provider's models are not this one's
        models.set_options([])
        models.disabled = True
        if provider is None:
            return
        await self._list_models(provider.name)

    async def _list_models(self, provider: str) -> None:
        models = self.query_one("#model", Select)
        try:
            listing = await self._mediator.send(ListModelsQuery(provider))
        except REFUSALS as error:
            self.notify(error.message, severity="error")
            return
        if listing.problem:
            self.notify(f"{listing.problem}; showing the recommended models.")
        choices, default = model_choices(listing, provider, self._defaults)
        _fill(models, choices, default)
        models.disabled = False

    def _show_key(self, provider: ProviderView | None) -> None:
        """The key: said when it is set, else asked."""
        missing = (
            provider is not None
            and provider.key is not None
            and not provider.key_set
            and provider.name not in self._keyed
        )
        state = self.query_one("#key-state", Static)
        state.display = not missing
        self.query_one("#key").display = missing
        self.query_one("#save").display = missing
        if provider is None:
            state.update("[dim]the provider's[/]")
        elif provider.key is None:
            state.update("[dim]none needed[/]")
        elif not missing:
            source = provider.key_source or "for this run"
            state.update(f"[green]✓[/] set ({source})")

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
        await self._list_models(provider)

    @on(Button.Pressed, "#run")
    def action_run(self) -> None:
        self._run()

    @work(exclusive=True, group="run")
    async def _run(self) -> None:
        """No confirmation: the form says what will happen. Only a missing provider package is
        asked about, before it is installed."""
        request, targets = self._request, self._picked_targets()
        provider = self.query_one("#provider", Select).value
        model = self.query_one("#model", Select).value
        if (
            request is None
            or not targets
            or not isinstance(provider, str)
            or not isinstance(model, str)
        ):
            self.notify("Pick a locale tree, a target and a model first.", severity="warning")
            return
        spec = f"{provider}:{model}"
        try:
            if self.query_one("#key", Input).value:
                await self._give_key()
            status = await self._mediator.send(GetProviderStatusQuery(ModelSpec(spec)))
            if not status.installed:
                question = (
                    f"The {status.provider} provider needs {status.package}, not installed. "
                    "Install it now?"
                )
                if not await self.app.push_screen_wait(ConfirmScreen(question)):
                    return
                self.notify(f"Installing {status.package}…")
                installed = await self._mediator.send(InstallProviderCommand(status.provider))
                self.notify(f"{installed.package} installed.")
        except REFUSALS as error:
            self.notify(error.message, severity="error")
            return
        save_answers(self._project, answers_of(request, targets, spec, self._shown))

        screen = RunScreen()
        await self.app.push_screen(screen)
        self._progress.target = screen
        command = GenerateLocalesCommand(
            request, targets, ModelSpec(spec), generation_options(self._settings)
        )
        try:
            receipt = await self._mediator.send(command)
        except REFUSALS as error:
            screen.stopped(error.message)
            return
        finally:
            self._progress.target = None
        output = self._shown(request.output) if request.output else None
        again = command_line(self._shown(request.path), targets, spec, request.source, output, [])
        screen.show_receipt(receipt, again)


def _row(
    label: str,
    *fields: Static | Input | Select[str] | SelectionList[str] | Checkbox,
    id: str | None = None,
) -> Horizontal:
    return Horizontal(Label(label), Vertical(*fields), classes="row", id=id)


def _fill(select: Select[str], choices: list[Choice], default: str | None) -> None:
    """`select`'s options, and the default when it is one of them."""
    select.set_options((choice.title, choice.value) for choice in choices)
    if default is not None and any(choice.value == default for choice in choices):
        select.value = default


def _count(number: int, noun: str) -> str:
    return f"{number} {noun}" if number == 1 else f"{number} {noun}s"
