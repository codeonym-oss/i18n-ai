"""The interactive mode: what a run was not told is asked, one step at a time, with the choices
the mediator's queries give (the trees in the project, CLDR's locales, the providers and their
models) and the last answers in this project as defaults."""

import os
import sys
from pathlib import Path

from mediary import Mediator
from rich.console import Console

from ...application.exports.locale import DetectLocaleTreesQuery, ListLocalesQuery, PresetMatch
from ...application.exports.provider import (
    ListModelsQuery,
    ListProvidersQuery,
    SetProviderKeyCommand,
)
from ...domain.exports.locale import LocaleCode
from ...runtime.answers import Answers, save_answers
from ..common.setup import (
    Choice,
    locale_choices,
    model_choices,
    output_choices,
    provider_choices,
    source_choices,
    tree_choices,
    within,
)
from .prompter import Prompter

_OTHER = "\0other"


def is_interactive(no_input: bool) -> bool:
    """Ask only a person at a terminal: not with --no-input, on CI, or when piped."""
    if no_input or os.environ.get("CI", "").lower() in ("1", "true", "yes"):
        return False
    return sys.stdin.isatty() and sys.stdout.isatty()


class Wizard:
    def __init__(
        self,
        prompter: Prompter,
        mediator: Mediator,
        console: Console,
        project: Path,
        answers: Answers,
    ) -> None:
        self._ask = prompter
        self._mediator = mediator
        self._console = console
        self._project = project
        self._last = answers
        self._shown = within(project)
        self.asked = False  # whether anything was asked, for the equivalent command
        self._keys: set[str] = set()  # the variables whose key was asked

    async def tree(self, preset: PresetMatch | None = None) -> Path:
        """The trees found in the project, the preset's first and the default, unless another
        was picked last time."""
        candidates = await self._mediator.send(DetectLocaleTreesQuery(self._project))
        self.asked = True
        choices, default = tree_choices(candidates, preset, self._last, self.shown)
        if not choices:
            self._console.print(f"[dim]No locale tree found under {self._project}.[/]")
            return Path(
                await self._ask.text("Path to the source locale tree", self._last.tree or "")
            )
        choices.append(Choice(_OTHER, "Another path…"))
        picked = await self._ask.select("Which locale tree?", choices, default)
        if picked == _OTHER:
            return Path(
                await self._ask.text("Path to the source locale tree", self._last.tree or "")
            )
        return Path(picked)

    async def source(self, locales: list[str]) -> LocaleCode:
        self.asked = True
        return LocaleCode(
            await self._ask.select(
                "Which locale is the source?", source_choices(locales), self._last.source
            )
        )

    async def targets(self, source: str, existing: tuple[str, ...]) -> tuple[LocaleCode, ...]:
        self.asked = True
        known = await self._mediator.send(ListLocalesQuery())
        choices, checked = locale_choices(known, existing, source, self._last)
        picked = await self._ask.checkbox("Which locales to generate?", choices, checked)
        return tuple(LocaleCode(code) for code in picked)

    async def output(self, beside: Path) -> Path | None:
        """None: beside the source."""
        choices, default = output_choices(beside, self._last, self.shown)
        choices.append(Choice(_OTHER, "Another directory…"))
        picked = await self._ask.select("Where do the new locales go?", choices, default)
        if picked == _OTHER:
            picked = await self._ask.text("Output directory", self._last.output or "")
        return Path(picked) if picked else None

    async def model(self) -> str:
        """The provider, its key when it is missing, then one of its models."""
        self.asked = True
        providers = await self._mediator.send(ListProvidersQuery())
        choices, default = provider_choices(providers, self._last)
        name = await self._ask.select("Which provider?", choices, default)
        provider = next(provider for provider in providers if provider.name == name)
        if provider.key and not provider.key_set:
            await self.key(provider.name, provider.key)

        listing = await self._mediator.send(ListModelsQuery(provider.name))
        if listing.problem:
            self._console.print(f"[dim]{listing.problem}; showing the recommended models.[/]")
        model = _OTHER
        if listing.models:
            choices, default = model_choices(listing, provider.name, self._last)
            choices.append(Choice(_OTHER, "Another model…"))
            model = await self._ask.select(f"Which {provider.name} model?", choices, default)
        while model == _OTHER or not model:
            model = await self._ask.text(f"The {provider.name} model's name")
        return f"{provider.name}:{model}"

    async def key(self, provider: str, variable: str) -> None:
        """The provider's key, used for this run, and saved in the system keyring only when the
        person says so. Asked once per run."""
        if variable in self._keys:
            return
        self._keys.add(variable)
        self.asked = True
        value = await self._ask.secret(f"{variable} (hidden)")
        if not value:
            self._console.print(f"[yellow]No {variable}: the provider may refuse the calls.[/]")
            return
        save = await self._ask.confirm("Save it in the system keyring for the next runs?", False)
        receipt = await self._mediator.send(SetProviderKeyCommand(provider, value, save))
        if receipt.saved:
            self._console.print(
                f"[green]✓[/] {variable} saved in the system keyring; "
                f"`i18n-ai auth logout {provider}` removes it."
            )
        elif receipt.problem:
            self._console.print(
                f"[yellow]{receipt.problem}: {variable} is used for this run only.[/]"
            )

    async def confirm(self, question: str) -> bool:
        return await self._ask.confirm(question, default=True)

    def remember(self, answers: Answers) -> None:
        save_answers(self._project, answers)

    def shown(self, path: Path) -> str:
        """`path` relative to the project when it is inside it."""
        return self._shown(path)
