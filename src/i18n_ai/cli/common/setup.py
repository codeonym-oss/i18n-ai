"""What a run is set up with, whoever asks for it: the prompts one question at a time, the TUI
as a form. The choices come from the mediator's queries (the trees in the project, CLDR's
locales, the providers and their models), with the last answers in this project as defaults."""

import shlex
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from ...application.exports.locale import (
    GenerationOptions,
    LocaleView,
    PresetMatch,
    TreeCandidateView,
)
from ...application.exports.provider import ModelsView, ProviderView
from ...application.ports.locale import TreeRequest
from ...domain.exports.locale import LocaleCode
from ...runtime.answers import Answers
from ...runtime.config import GenerationConfig

# A path as the person sees it: relative to the project when it is inside it.
Shown = Callable[[Path], str]


def within(project: Path) -> Shown:
    """Paths shown relative to `project` when they are inside it."""

    def shown(path: Path) -> str:
        absolute = path.expanduser().resolve()
        try:
            return absolute.relative_to(project.resolve()).as_posix() or "."
        except ValueError:
            return str(path)

    return shown


@dataclass(frozen=True)
class Choice:
    value: str
    title: str


def tree_choices(
    candidates: Iterable[TreeCandidateView], preset: PresetMatch | None, last: Answers, shown: Shown
) -> tuple[list[Choice], str | None]:
    """The trees found in the project, the preset's first and the default, unless another was
    picked last time. No choice when none was found."""
    ours = preset.tree if preset is not None else None
    if ours is not None:
        candidates = [
            candidate for candidate in candidates if candidate.path.resolve() != ours.resolve()
        ]
    choices = [
        Choice(
            shown(candidate.path),
            f"{shown(candidate.path)}  "
            f"[{candidate.layout}, {'+'.join(candidate.formats)}: {_some(candidate.locales)}]",
        )
        for candidate in candidates
    ]
    if preset is not None and ours is not None:
        choices.insert(0, Choice(shown(ours), f"{shown(ours)}  [{preset.preset.name} preset]"))
    if not choices:
        return [], None
    return choices, last.tree or (shown(ours) if ours is not None else None)


def source_choices(locales: Iterable[str]) -> list[Choice]:
    return [Choice(code, _title(LocaleCode(code))) for code in locales]


def locale_choices(
    known: Iterable[LocaleView], existing: Sequence[str], source: str, last: Answers
) -> tuple[list[Choice], set[str]]:
    """The target locales: those in the tree first, then CLDR's; checked, those in the tree and
    those picked last time."""
    present = [LocaleCode(code) for code in existing]
    choices = [Choice(locale.value, f"{_title(locale)} · in the tree") for locale in present]
    taken = {locale.key for locale in [*present, LocaleCode(source)]}
    for view in known:
        locale = LocaleCode(view.code)
        if locale.key not in taken:
            choices.append(Choice(locale.value, _title(locale)))
    return choices, {*existing, *last.targets} - {source}


def output_choices(beside: Path, last: Answers, shown: Shown) -> tuple[list[Choice], str | None]:
    """Where the targets go: "" is beside the source."""
    choices = [Choice("", f"Beside the source ({shown(beside)})")]
    if last.output:
        choices.insert(0, Choice(last.output, f"{last.output} (last time)"))
    return choices, last.output


def provider_choices(
    providers: Iterable[ProviderView], last: Answers
) -> tuple[list[Choice], str | None]:
    """The providers, those with a key or installed first."""
    ordered = sorted(
        providers,
        key=lambda provider: (not (provider.installed or provider.key_set), provider.name),
    )
    last_provider = (last.model or "").partition(":")[0]
    return [Choice(provider.name, _provider_title(provider)) for provider in ordered], (
        last_provider or None
    )


def model_choices(
    listing: ModelsView, provider: str, last: Answers
) -> tuple[list[Choice], str | None]:
    """A provider's models; the default, the one picked last time with it."""
    last_provider, _, last_model = (last.model or "").partition(":")
    choices = [
        Choice(model.id, f"{model.id}  · recommended" if model.recommended else model.id)
        for model in listing.models
    ]
    return choices, last_model if last_provider == provider else None


def generation_options(
    defaults: GenerationConfig,
    *,
    context: str | None = None,
    batch_size: int | None = None,
    concurrency: int | None = None,
    max_attempts: int | None = None,
    classify: bool = True,
    overwrite: bool = False,
    strict: bool = False,
    temperature: float | None = None,
) -> GenerationOptions:
    """The options given, the settings' for the others."""
    return GenerationOptions(
        context=context,
        batch_size=batch_size or defaults.batch_size,
        concurrency=concurrency or defaults.concurrency,
        max_attempts=max_attempts or defaults.max_attempts,
        classify=classify,
        overwrite=overwrite,
        strict=strict,
        temperature=temperature,
    )


def answers_of(
    tree: TreeRequest, targets: Iterable[LocaleCode], model: str, shown: Shown
) -> Answers:
    """What to remember of a run, for the next one's defaults."""
    return Answers(
        tree=shown(tree.path),
        source=tree.source.value if tree.source else None,
        targets=[target.value for target in targets],
        output=shown(tree.output) if tree.output else None,
        model=model,
    )


@dataclass(frozen=True)
class Planned:
    """A run's targets, files left out and single (file, target) pairs skipped, from a plan's
    cells turned off."""

    targets: tuple[LocaleCode, ...]
    exclude: tuple[str, ...]
    skip: frozenset[tuple[PurePosixPath, LocaleCode]]


def planned(
    files: Sequence[str], targets: Sequence[LocaleCode], off: set[tuple[str, str]]
) -> Planned:
    """A target whose every cell is `off` leaves the targets, a file whose every cell is off is
    excluded, and the other cells off are skipped. `off` holds (file name, locale) pairs."""
    kept = tuple(
        target for target in targets if any((file, target.value) not in off for file in files)
    )
    gone = [file for file in files if all((file, target.value) in off for target in targets)]
    skip = frozenset(
        (PurePosixPath(file), target)
        for file in files
        if file not in gone
        for target in kept
        if (file, target.value) in off
    )
    return Planned(kept, tuple(_literal(file) for file in gone), skip)


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


def _literal(name: str) -> str:
    """A glob that matches `name` alone."""
    return "".join(f"[{char}]" if char in "*?[" else char for char in name)


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
