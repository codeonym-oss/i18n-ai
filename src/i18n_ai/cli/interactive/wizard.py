"""The interactive mode: what a run was not told is asked, one step at a time, with the choices
the mediator's queries give (the trees in the project, CLDR's locales, the providers and their
models) and the last answers in this project as defaults."""

import os
import shlex
import sys
from pathlib import Path

from mediary import Mediator
from rich.console import Console

from ...application.exports.locale import DetectLocaleTreesQuery, ListLocalesQuery
from ...application.exports.provider import (
    ListModelsQuery,
    ListProvidersQuery,
    ProviderView,
    SetProviderKeyCommand,
)
from ...domain.exports.locale import LocaleCode
from ...runtime.answers import Answers, save_answers
from .prompter import Choice, Prompter

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
        self.asked = False  # whether anything was asked, for the equivalent command
        self._keys: set[str] = set()  # the variables whose key was asked

    async def tree(self) -> Path:
        candidates = await self._mediator.send(DetectLocaleTreesQuery(self._project))
        self.asked = True
        if not candidates:
            self._console.print(f"[dim]No locale tree found under {self._project}.[/]")
            return Path(
                await self._ask.text("Path to the source locale tree", self._last.tree or "")
            )
        choices = [
            Choice(
                self.shown(candidate.path),
                f"{self.shown(candidate.path)}  [{candidate.layout}: {_some(candidate.locales)}]",
            )
            for candidate in candidates
        ]
        choices.append(Choice(_OTHER, "Another path…"))
        picked = await self._ask.select("Which locale tree?", choices, self._last.tree)
        if picked == _OTHER:
            return Path(
                await self._ask.text("Path to the source locale tree", self._last.tree or "")
            )
        return Path(picked)

    async def source(self, locales: list[str]) -> LocaleCode:
        self.asked = True
        choices = [Choice(code, _title(LocaleCode(code))) for code in locales]
        return LocaleCode(
            await self._ask.select("Which locale is the source?", choices, self._last.source)
        )

    async def targets(self, source: str, existing: tuple[str, ...]) -> tuple[LocaleCode, ...]:
        self.asked = True
        origin = LocaleCode(source)
        known = await self._mediator.send(ListLocalesQuery())
        present = [LocaleCode(code) for code in existing]
        choices = [Choice(locale.value, f"{_title(locale)} · in the tree") for locale in present]
        taken = {locale.key for locale in [*present, origin]}
        for view in known:
            locale = LocaleCode(view.code)
            if locale.key not in taken:
                choices.append(Choice(locale.value, _title(locale)))
        checked = {*existing, *self._last.targets} - {source}
        picked = await self._ask.checkbox("Which locales to generate?", choices, checked)
        return tuple(LocaleCode(code) for code in picked)

    async def output(self, beside: Path) -> Path | None:
        """None: beside the source."""
        choices = [Choice("", f"Beside the source ({self.shown(beside)})")]
        if self._last.output:
            choices.insert(0, Choice(self._last.output, f"{self._last.output} (last time)"))
        choices.append(Choice(_OTHER, "Another directory…"))
        picked = await self._ask.select("Where do the new locales go?", choices, self._last.output)
        if picked == _OTHER:
            picked = await self._ask.text("Output directory", self._last.output or "")
        return Path(picked) if picked else None

    async def model(self) -> str:
        """The provider, its key when it is missing, then one of its models."""
        self.asked = True
        providers = sorted(
            await self._mediator.send(ListProvidersQuery()),
            key=lambda provider: (not (provider.installed or provider.key_set), provider.name),
        )
        last_provider, _, last_model = (self._last.model or "").partition(":")
        choices = [Choice(provider.name, _provider_title(provider)) for provider in providers]
        name = await self._ask.select("Which provider?", choices, last_provider or None)
        provider = next(provider for provider in providers if provider.name == name)
        if provider.key and not provider.key_set:
            await self.key(provider.name, provider.key)

        listing = await self._mediator.send(ListModelsQuery(provider.name))
        if listing.problem:
            self._console.print(f"[dim]{listing.problem}; showing the recommended models.[/]")
        model = _OTHER
        if listing.models:
            choices = [
                Choice(model.id, f"{model.id}  · recommended" if model.recommended else model.id)
                for model in listing.models
            ]
            choices.append(Choice(_OTHER, "Another model…"))
            default = last_model if last_provider == provider.name else None
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
        absolute = path.expanduser().resolve()
        try:
            return absolute.relative_to(self._project.resolve()).as_posix() or "."
        except ValueError:
            return str(path)


def command_line(
    path: str,
    targets: tuple[LocaleCode, ...],
    model: str | None,
    source: LocaleCode | None,
    output: str | None,
    flags: list[str],
) -> str:
    """The `i18n-ai generate` command that repeats a run without asking anything."""
    words = ["i18n-ai", "generate", path, "-t", ",".join(target.value for target in targets)]
    if source is not None:
        words += ["-s", source.value]
    if output is not None:
        words += ["-o", output]
    if model is not None:
        words += ["-m", model]
    return shlex.join([*words, *flags])


def _title(locale: LocaleCode) -> str:
    rtl = " (rtl)" if locale.direction == "rtl" else ""
    return f"{locale.value} — {locale.display_name}{rtl}"


def _some(locales: tuple[str, ...], shown: int = 6) -> str:
    more = f" +{len(locales) - shown}" if len(locales) > shown else ""
    return ", ".join(locales[:shown]) + more


def _provider_title(provider: ProviderView) -> str:
    tags = [
        tag for tag, on in (("key set", provider.key_set), ("installed", provider.installed)) if on
    ]
    return f"{provider.name}  ({', '.join(tags)})" if tags else provider.name
