from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from i18n_ai.application.exports.locale import (
    LocaleView,
    PresetMatch,
    PresetView,
    TreeCandidateView,
)
from i18n_ai.application.exports.provider import ModelsView, ModelView, ProviderView
from i18n_ai.application.ports.locale import TreeRequest
from i18n_ai.cli.common.setup import (
    Choice,
    answers_of,
    generation_options,
    locale_choices,
    model_choices,
    output_choices,
    provider_choices,
    tree_choices,
)
from i18n_ai.domain.exports.locale import LocaleCode
from i18n_ai.runtime.answers import Answers
from i18n_ai.runtime.config import GenerationConfig

if TYPE_CHECKING:
    from i18n_ai.application.ports.provider import KeySource


@pytest.fixture
def laravel_preset() -> PresetMatch:
    view = PresetView("laravel", "Laravel", "", ("composer.json",), "json", (":name",), "laravel")
    return PresetMatch(view, "laravel/framework in composer.json", Path("lang"), None)


def shown(path: Path) -> str:
    return path.as_posix()


def candidate(path: str, *locales: str) -> TreeCandidateView:
    return TreeCandidateView(Path(path), "directory", locales, None, ("json",))


def provider(name: str, installed: bool = False, key_set: bool = False) -> ProviderView:
    source: KeySource | None = "env" if key_set else None
    return ProviderView(name, f"langchain-{name}", installed, f"{name.upper()}_API_KEY", source)


def test_the_presets_tree_comes_first_and_is_the_default(laravel_preset: PresetMatch) -> None:
    choices, default = tree_choices(
        (candidate("public/locales", "en", "fr"), candidate("lang", "en")),
        laravel_preset,
        Answers(),
        shown,
    )

    assert [choice.value for choice in choices] == ["lang", "public/locales"]
    assert choices[0].title == "lang  [laravel preset]"
    assert choices[1].title == "public/locales  [directory, json: en, fr]"
    assert default == "lang"


def test_the_last_tree_is_the_default_over_the_presets(laravel_preset: PresetMatch) -> None:
    _, default = tree_choices((), laravel_preset, Answers(tree="public/locales"), shown)

    assert default == "public/locales"


def test_no_tree_found_gives_no_choice() -> None:
    assert tree_choices((), None, Answers(), shown) == ([], None)


def test_the_locales_in_the_tree_come_first_and_are_checked() -> None:
    known = (
        LocaleView("en", "English", "ltr"),
        LocaleView("de", "German", "ltr"),
        LocaleView("fr", "French", "ltr"),
    )

    choices, checked = locale_choices(known, ("fr",), "en", Answers(targets=["de", "en"]))

    assert [choice.value for choice in choices] == ["fr", "de"]
    assert choices[0].title == "fr — French · in the tree"
    assert checked == {"fr", "de"}


def test_the_output_is_beside_the_source_unless_another_was_picked() -> None:
    assert output_choices(Path("lang"), Answers(), shown) == (
        [Choice("", "Beside the source (lang)")],
        None,
    )
    choices, default = output_choices(Path("lang"), Answers(output="out"), shown)

    assert choices[0] == Choice("out", "out (last time)")
    assert default == "out"


def test_the_providers_with_a_key_or_installed_come_first() -> None:
    providers = (provider("anthropic"), provider("openai", key_set=True), provider("ollama", True))

    choices, default = provider_choices(providers, Answers(model="anthropic:claude"))

    assert choices == [
        Choice("ollama", "ollama  (installed)"),
        Choice("openai", "openai  (key set)"),
        Choice("anthropic", "anthropic"),
    ]
    assert default == "anthropic"


def test_the_last_model_is_the_default_for_its_provider_only() -> None:
    listing = ModelsView(
        "openai",
        (ModelView("gpt-4.1-mini", True, None), ModelView("gpt-4.1", False, None)),
        True,
        None,
    )

    choices, default = model_choices(listing, "openai", Answers(model="openai:gpt-4.1"))

    assert choices == [
        Choice("gpt-4.1-mini", "gpt-4.1-mini  · recommended"),
        Choice("gpt-4.1", "gpt-4.1"),
    ]
    assert default == "gpt-4.1"
    assert model_choices(listing, "openai", Answers(model="ollama:gpt-4.1"))[1] is None


def test_the_options_fall_back_on_the_settings() -> None:
    defaults = GenerationConfig(batch_size=10, concurrency=2, max_attempts=5)

    options = generation_options(defaults, concurrency=4, overwrite=True)

    assert (options.batch_size, options.concurrency, options.max_attempts) == (10, 4, 5)
    assert options.overwrite
    assert not options.strict
    assert options.classify


def test_the_answers_are_what_was_picked() -> None:
    tree = TreeRequest(path=Path("lang"), source=LocaleCode("en"), output=Path("out"))

    answers = answers_of(tree, (LocaleCode("fr"), LocaleCode("de")), "openai:gpt-4.1", shown)

    assert answers == Answers("lang", "en", ["fr", "de"], "out", "openai:gpt-4.1")
