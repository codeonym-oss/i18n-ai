import json
from collections.abc import AsyncIterator
from pathlib import Path

import pytest
from mediary import Mediator
from rich.console import Console

from i18n_ai.application.exports.locale import (
    GenerateLocalesCommand,
    GenerationOptions,
    ResultStatus,
    ScanLocaleTreeQuery,
)
from i18n_ai.application.ports.locale import TreeRequest
from i18n_ai.di.container import build_container
from i18n_ai.di.messaging import build_mediator
from i18n_ai.domain.exports.locale import LocaleCode, TargetIsSource
from i18n_ai.domain.exports.provider import ModelSpec
from support.fakes import FakeGateway, FakeModel

MODEL = ModelSpec("openai:fake-model")


@pytest.fixture
def gateway() -> FakeGateway:
    return FakeGateway()


@pytest.fixture
async def mediator(gateway: FakeGateway) -> AsyncIterator[Mediator]:
    container = build_container(build_mediator(), Console(quiet=True), FakeModel(gateway))
    async with container() as request:
        yield await request.get(Mediator)
    await container.close()


def read(path: Path) -> dict:  # type: ignore[type-arg]
    return json.loads(path.read_text(encoding="utf-8"))


def codes(*values: str) -> tuple[LocaleCode, ...]:
    return tuple(LocaleCode(value) for value in values)


async def test_a_directory_tree_is_generated_beside_its_source(
    mediator: Mediator, examples: Path
) -> None:
    locales = examples / "i18next" / "locales"
    command = GenerateLocalesCommand(TreeRequest(locales / "en"), codes("ar", "fr"), MODEL)

    receipt = await mediator.send(command)

    statuses = {(r.file, r.target): r.status for r in receipt.results}
    assert statuses[("meta.json", None)] == ResultStatus.IGNORED
    assert statuses[("common.json", "ar")] == ResultStatus.WRITTEN
    assert statuses[("auth/login.json", "fr")] == ResultStatus.WRITTEN

    arabic = read(locales / "ar" / "common.json")
    assert [key for key in arabic["cart"] if key.startswith("item_")] == [
        "item_zero",
        "item_one",
        "item_two",
        "item_few",
        "item_many",
        "item_other",
    ]
    assert arabic["app"]["welcome"] == "[ar] Welcome back, {{name}}!"
    assert arabic["maxItems"] == 50
    assert arabic["beta"] is False
    assert arabic["footer"].endswith("reserved.  ")
    assert (locales / "ar" / "auth" / "login.json").is_file()


async def test_good_existing_translations_are_kept(mediator: Mediator, examples: Path) -> None:
    locales = examples / "i18next" / "locales"

    receipt = await mediator.send(
        GenerateLocalesCommand(TreeRequest(locales / "en"), codes("fr"), MODEL)
    )

    french = read(locales / "fr" / "common.json")
    assert french["app"]["title"] == "Tableau de bord Acme"  # kept
    assert french["app"]["welcome"] == "[fr] Welcome back, {{name}}!"  # {{nom}} was broken
    assert french["nav"]["logout"] == "[fr] Log out"  # was missing
    common = next(r for r in receipt.results if r.file == "common.json")
    assert common.reused == 3


async def test_a_rejected_message_is_sent_back_with_its_problem(examples: Path) -> None:
    gateway = FakeGateway(broken_first={"app.welcome"})
    container = build_container(build_mediator(), Console(quiet=True), FakeModel(gateway))
    async with container() as request:
        mediator = await request.get(Mediator)
        locales = examples / "i18next" / "locales"
        command = GenerateLocalesCommand(
            TreeRequest(locales / "en", include=("common.json",)), codes("de"), MODEL
        )
        receipt = await mediator.send(command)
    await container.close()

    (result,) = [r for r in receipt.results if r.target == "de"]
    assert result.status == ResultStatus.WRITTEN
    retried = [batch for batch in gateway.batches if batch.problems]
    assert len(retried) == 1
    assert "missing {{name}}" in next(iter(retried[0].problems.values()))[0]
    assert read(locales / "de" / "common.json")["app"]["welcome"] == "[de] Welcome back, {{name}}!"


async def test_a_message_that_keeps_failing_falls_back_or_is_refused(examples: Path) -> None:
    class Stubborn(FakeGateway):
        async def translate(self, batch):  # type: ignore[no-untyped-def]
            answers = await super().translate(batch)
            return {unit_id: text.replace("{{name}}", "") for unit_id, text in answers.items()}

    gateway = Stubborn()
    container = build_container(build_mediator(), Console(quiet=True), FakeModel(gateway))
    async with container() as request:
        mediator = await request.get(Mediator)
        locales = examples / "i18next" / "locales"
        tree = TreeRequest(locales / "en", include=("common.json",))
        partial = await mediator.send(GenerateLocalesCommand(tree, codes("it"), MODEL))
        strict = await mediator.send(
            GenerateLocalesCommand(
                tree, codes("nl"), MODEL, GenerationOptions(strict=True, max_attempts=2)
            )
        )
    await container.close()

    (result,) = [r for r in partial.results if r.target == "it"]
    assert result.status == ResultStatus.PARTIAL
    assert read(locales / "it" / "common.json")["app"]["welcome"] == "Welcome back, {{name}}!"
    (refused,) = [r for r in strict.results if r.target == "nl"]
    assert refused.status == ResultStatus.REFUSED
    assert not (locales / "nl").exists()


async def test_the_classifier_can_ignore_a_file(examples: Path) -> None:
    gateway = FakeGateway(refuse={"auth/login.json"})
    container = build_container(build_mediator(), Console(quiet=True), FakeModel(gateway))
    async with container() as request:
        mediator = await request.get(Mediator)
        locales = examples / "i18next" / "locales"
        receipt = await mediator.send(
            GenerateLocalesCommand(TreeRequest(locales / "en"), codes("es"), MODEL)
        )
    await container.close()

    ignored = {r.file for r in receipt.results if r.status == ResultStatus.IGNORED}
    assert ignored == {"meta.json", "auth/login.json"}
    assert not (locales / "es" / "auth").exists()


async def test_an_icu_file_layout(mediator: Mediator, examples: Path) -> None:
    messages = examples / "icu" / "messages"

    receipt = await mediator.send(
        GenerateLocalesCommand(TreeRequest(messages / "en.json"), codes("pt-BR"), MODEL)
    )

    assert [r.status for r in receipt.results] == [ResultStatus.WRITTEN]
    assert read(messages / "pt-BR.json")["Inbox"]["title"] == "[pt-BR] Inbox"


async def test_a_bundle_keeps_its_other_locales(mediator: Mediator, examples: Path) -> None:
    bundle = examples / "bundle" / "i18n.json"

    await mediator.send(GenerateLocalesCommand(TreeRequest(bundle), codes("fr"), MODEL))

    content = read(bundle)
    assert list(content) == ["en", "es", "fr"]
    assert content["fr"]["files"] == "[fr] %d files selected"
    assert content["es"] == {"greeting": "¡Hola, %{name}!"}


async def test_the_scan_refuses_the_source_as_a_target(mediator: Mediator, examples: Path) -> None:
    with pytest.raises(TargetIsSource):
        await mediator.send(
            ScanLocaleTreeQuery(TreeRequest(examples / "i18next" / "locales"), codes("EN"))
        )
