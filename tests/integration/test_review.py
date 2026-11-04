import json
from pathlib import Path, PurePosixPath

import pytest
from mediary import Mediator
from rich.console import Console

from i18n_ai.application.exports.locale import (
    AcceptFallbacksCommand,
    GenerateLocalesCommand,
    GenerationOptions,
    ListFallbacksQuery,
    RetryFallbacksCommand,
    SetMessageCommand,
)
from i18n_ai.application.ports.locale import MessageRef, TreeRequest
from i18n_ai.di.container import build_container
from i18n_ai.di.messaging import build_mediator
from i18n_ai.domain.exports.locale import KeyPath, LocaleCode, MessageUnknown, TargetNotGenerated
from i18n_ai.domain.exports.provider import ModelSpec
from support.fakes import FakeGateway, FakeModel

MODEL = ModelSpec("openai:fake-model")
RECORD = ".i18n-ai-fallbacks.json"
WELCOME = KeyPath(("app", "welcome"))
TOTAL = KeyPath(("cart", "total"))


class Stubborn(FakeGateway):
    """Loses `placeholders` in every translation, so their messages fall back."""

    def __init__(self, *placeholders: str) -> None:
        super().__init__()
        self.placeholders = placeholders or ("{{name}}",)

    async def translate(self, batch):  # type: ignore[no-untyped-def]
        answers = await super().translate(batch)
        for placeholder in self.placeholders:
            answers = {key: text.replace(placeholder, "") for key, text in answers.items()}
        return answers


async def send(gateway: FakeGateway, request):  # type: ignore[no-untyped-def]
    container = build_container(build_mediator(), Console(quiet=True), FakeModel(gateway))
    async with container() as scope:
        mediator = await scope.get(Mediator)
        result = await mediator.send(request)
    await container.close()
    return result


def read(path: Path) -> dict:  # type: ignore[type-arg]
    return json.loads(path.read_text(encoding="utf-8"))


async def fallen(gateway: FakeGateway, locales: Path, *targets: str) -> None:
    """A run of `common.json` into `targets` that leaves fallbacks."""
    tree = TreeRequest(locales / "en", include=("common.json",))
    codes = tuple(LocaleCode(target) for target in targets)
    await send(
        gateway, GenerateLocalesCommand(tree, codes, MODEL, GenerationOptions(max_attempts=2))
    )


def ref(target: str, path: KeyPath) -> MessageRef:
    return MessageRef(PurePosixPath("common.json"), LocaleCode(target), path)


async def test_the_fallbacks_are_listed_with_their_source(examples: Path) -> None:
    locales = examples / "i18next" / "locales"
    await fallen(Stubborn(), locales, "it")

    view = await send(FakeGateway(), ListFallbacksQuery(TreeRequest(locales / "en")))

    (entry,) = view.entries
    assert entry.ref == ref("it", WELCOME)
    assert entry.source == "Welcome back, {{name}}!"
    assert entry.current == "Welcome back, {{name}}!"
    assert entry.entry.rejected == "[it] Welcome back, !"
    assert [problem.rule for problem in entry.entry.problems] == ["placeholders"]


async def test_a_file_left_out_by_the_tree_still_has_its_fallbacks(examples: Path) -> None:
    locales = examples / "i18next" / "locales"
    await fallen(Stubborn(), locales, "it")

    view = await send(
        FakeGateway(), ListFallbacksQuery(TreeRequest(locales / "en", include=("auth/*",)))
    )

    (entry,) = view.entries
    assert not entry.stale


async def test_an_entry_whose_message_is_gone_is_stale(examples: Path) -> None:
    locales = examples / "i18next" / "locales"
    await fallen(Stubborn(), locales, "it")
    source = locales / "en" / "common.json"
    content = read(source)
    del content["app"]["welcome"]
    source.write_text(json.dumps(content), encoding="utf-8")

    view = await send(FakeGateway(), ListFallbacksQuery(TreeRequest(locales / "en")))

    (entry,) = view.entries
    assert entry.stale
    assert (entry.ref, entry.source) == (None, None)
    assert entry.entry.path == WELCOME


async def test_a_tree_without_a_record_has_nothing_to_review(examples: Path) -> None:
    locales = examples / "i18next" / "locales"

    view = await send(FakeGateway(), ListFallbacksQuery(TreeRequest(locales / "en")))

    assert view.entries == ()


async def test_a_good_text_is_written_and_leaves_the_record(examples: Path) -> None:
    locales = examples / "i18next" / "locales"
    await fallen(Stubborn(), locales, "it")

    result = await send(
        FakeGateway(),
        SetMessageCommand(TreeRequest(locales / "en"), ref("it", WELCOME), "Bentornato, {{name}}!"),
    )

    assert result.written
    assert read(locales / "it" / "common.json")["app"]["welcome"] == "Bentornato, {{name}}!"
    assert not (locales / RECORD).exists()


async def test_a_text_that_breaks_a_rule_is_refused_and_nothing_changes(examples: Path) -> None:
    locales = examples / "i18next" / "locales"
    await fallen(Stubborn(), locales, "it")
    target, record = locales / "it" / "common.json", locales / RECORD
    before = target.read_bytes(), record.read_bytes()

    result = await send(
        FakeGateway(),
        SetMessageCommand(TreeRequest(locales / "en"), ref("it", WELCOME), "Bentornato!"),
    )

    assert not result.written
    assert [violation.message for violation in result.violations] == ["missing {{name}}"]
    assert (target.read_bytes(), record.read_bytes()) == before


async def test_a_message_that_is_no_fallback_is_set_and_the_record_kept(examples: Path) -> None:
    locales = examples / "i18next" / "locales"
    await fallen(Stubborn(), locales, "it")
    record = (locales / RECORD).read_bytes()

    result = await send(
        FakeGateway(),
        SetMessageCommand(
            TreeRequest(locales / "en"), ref("it", KeyPath(("nav", "home"))), "Pagina iniziale"
        ),
    )

    assert result.written
    assert read(locales / "it" / "common.json")["nav"]["home"] == "Pagina iniziale"
    assert (locales / RECORD).read_bytes() == record


async def test_a_path_that_is_no_message_or_a_target_never_generated_is_refused(
    examples: Path,
) -> None:
    locales = examples / "i18next" / "locales"
    await fallen(Stubborn(), locales, "it")
    tree = TreeRequest(locales / "en")

    with pytest.raises(MessageUnknown):
        await send(FakeGateway(), SetMessageCommand(tree, ref("it", KeyPath(("app", "nope"))), "x"))
    with pytest.raises(TargetNotGenerated):
        await send(
            FakeGateway(), SetMessageCommand(tree, ref("de", WELCOME), "Willkommen, {{name}}!")
        )


class Again(Stubborn):
    """Loses `{{name}}` again, in other words."""

    async def translate(self, batch):  # type: ignore[no-untyped-def]
        answers = await super().translate(batch)
        return {key: f"{text} (again)" for key, text in answers.items()}


def recorded(locales: Path) -> list[tuple[str, tuple[str, ...], str | None]]:
    return [
        (entry["file"], tuple(entry["path"]), entry["rejected"])
        for entry in read(locales / RECORD)["fallbacks"]
    ]


async def test_a_retry_translates_only_the_chosen_fallbacks(examples: Path) -> None:
    locales = examples / "i18next" / "locales"
    await fallen(Stubborn("{{name}}", "{{amount, currency(EUR)}}"), locales, "it")
    assert len(recorded(locales)) == 2
    gateway = FakeGateway()

    receipt = await send(
        gateway, RetryFallbacksCommand(TreeRequest(locales / "en"), MODEL, (ref("it", WELCOME),))
    )

    sent = [str(unit.path) for batch in gateway.batches for unit in batch.units]
    assert sent == ["app.welcome"]
    assert gateway.classified == []
    assert receipt.ok
    italian = read(locales / "it" / "common.json")
    assert italian["app"]["welcome"] == "[it] Welcome back, {{name}}!"
    assert italian["cart"]["total"] == "Total: {{amount, currency(EUR)}}"
    assert recorded(locales) == [("it/common.json", ("cart", "total"), "[it] Total:")]


async def test_a_fallback_that_fails_again_is_recorded_anew(examples: Path) -> None:
    locales = examples / "i18next" / "locales"
    await fallen(Stubborn("{{name}}", "{{amount, currency(EUR)}}"), locales, "it")

    await send(
        Again(), RetryFallbacksCommand(TreeRequest(locales / "en"), MODEL, (ref("it", WELCOME),))
    )

    assert recorded(locales) == [
        ("it/common.json", ("app", "welcome"), "[it] Welcome back, ! (again)"),
        ("it/common.json", ("cart", "total"), "[it] Total:"),
    ]
    assert read(locales / "it" / "common.json")["app"]["welcome"] == "Welcome back, {{name}}!"


async def test_an_accepted_fallback_leaves_the_record_and_the_file_alone(examples: Path) -> None:
    locales = examples / "i18next" / "locales"
    await fallen(Stubborn("{{name}}", "{{amount, currency(EUR)}}"), locales, "it")
    tree = TreeRequest(locales / "en")
    target = locales / "it" / "common.json"
    before = target.stat().st_mtime_ns, target.read_bytes()
    welcome, total = (
        entry.entry for entry in (await send(FakeGateway(), ListFallbacksQuery(tree))).entries
    )

    await send(FakeGateway(), AcceptFallbacksCommand(tree, (welcome,)))
    assert [path for _, path, _ in recorded(locales)] == [("cart", "total")]

    await send(FakeGateway(), AcceptFallbacksCommand(tree, (total,)))
    assert not (locales / RECORD).exists()
    assert (target.stat().st_mtime_ns, target.read_bytes()) == before


async def test_a_stale_entry_can_be_accepted(examples: Path) -> None:
    locales = examples / "i18next" / "locales"
    await fallen(Stubborn(), locales, "it")
    (locales / "en" / "common.json").unlink()
    tree = TreeRequest(locales / "en")
    (entry,) = (await send(FakeGateway(), ListFallbacksQuery(tree))).entries
    assert entry.stale

    await send(FakeGateway(), AcceptFallbacksCommand(tree, (entry.entry,)))

    assert not (locales / RECORD).exists()
