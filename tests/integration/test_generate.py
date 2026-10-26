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
from i18n_ai.domain.exports.locale import KeyPath, LocaleCode, MessageSyntax, TargetIsSource
from i18n_ai.domain.exports.provider import ModelSpec
from support.fakes import FakeGateway, FakeModel

MODEL = ModelSpec("openai:fake-model")
# A machine's translation, for review
REVIEW = '<target state="needs-review-translation" state-qualifier="mt-suggestion">'


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


class Stubborn(FakeGateway):
    """Loses `placeholder` in every translation, so its messages fall back."""

    def __init__(self, placeholder: str = "{{name}}") -> None:
        super().__init__()
        self.placeholder = placeholder

    async def translate(self, batch):  # type: ignore[no-untyped-def]
        answers = await super().translate(batch)
        return {unit_id: text.replace(self.placeholder, "") for unit_id, text in answers.items()}


async def test_a_message_that_keeps_failing_falls_back_or_is_refused(examples: Path) -> None:
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


async def test_a_rails_tree_keeps_its_comments_and_its_root(
    mediator: Mediator, examples: Path
) -> None:
    locales = examples / "rails" / "config" / "locales"

    receipt = await mediator.send(GenerateLocalesCommand(TreeRequest(locales), codes("fr"), MODEL))

    assert receipt.ok
    french = (locales / "fr.yml").read_text(encoding="utf-8")
    assert french.startswith("# Files in the config/locales directory")
    assert '\nfr:\n  hello: "[fr] Hello world"\n' in french
    assert "      title: '[fr] Users' # the page's heading\n" in french
    assert "      bio: |\n        [fr] Tell us about yourself.\n" in french
    assert "  # The settings page\n" in french
    assert "      - :year\n" in french  # a symbol, not text
    assert "    per_page: 25\n" in french
    assert "        zero: '[fr] No users'\n" in french  # Rails' zero, kept
    assert '        one: "[fr] 1 user"\n        many: "[fr] %{count} users"\n' in french  # as other


async def test_a_rails_plural_takes_the_targets_forms(mediator: Mediator, examples: Path) -> None:
    locales = examples / "rails" / "config" / "locales"

    receipt = await mediator.send(GenerateLocalesCommand(TreeRequest(locales), codes("ar"), MODEL))

    assert receipt.ok
    arabic = (locales / "ar.yml").read_text(encoding="utf-8")
    assert (
        "      count:\n"
        "        zero: '[ar] No users'\n"
        '        one: "[ar] 1 user"\n'
        '        two: "[ar] %{count} users"\n'
        '        few: "[ar] %{count} users"\n'
        '        many: "[ar] %{count} users"\n'
        '        other: "[ar] %{count} users"\n'
    ) in arabic


async def test_a_rooted_target_keeps_its_good_translations(
    mediator: Mediator, examples: Path, gateway: FakeGateway
) -> None:
    locales = examples / "rails" / "config" / "locales"
    (locales / "de.yml").write_text('de:\n  hello: "Hallo Welt"\n', encoding="utf-8")

    await mediator.send(GenerateLocalesCommand(TreeRequest(locales), codes("de"), MODEL))

    german = (locales / "de.yml").read_text(encoding="utf-8")
    assert 'hello: "Hallo Welt"' in german
    sent = [unit.source for batch in gateway.batches for unit in batch.units]
    assert "Hello world" not in sent


async def test_a_vue_i18n_tree_in_yaml(mediator: Mediator, examples: Path) -> None:
    locales = examples / "vue-i18n" / "locales"

    report = await mediator.send(ScanLocaleTreeQuery(TreeRequest(locales), codes("ja")))
    await mediator.send(GenerateLocalesCommand(TreeRequest(locales), codes("ja"), MODEL))

    assert report.format == "yaml"
    assert report.targets[0].files[0].path == locales / "ja.yaml"
    japanese = (locales / "ja.yaml").read_text(encoding="utf-8")
    assert japanese.startswith("# The storefront's messages, read by vue-i18n.\napp:\n")
    assert '  checkout: "[ja] @:app.title checkout"\n' in japanese
    assert "  links:\n  - '[ja] About us'\n" in japanese


async def test_a_flutter_tree_in_arb(
    mediator: Mediator, examples: Path, gateway: FakeGateway
) -> None:
    l10n = examples / "flutter" / "lib" / "l10n"

    receipt = await mediator.send(
        GenerateLocalesCommand(TreeRequest(l10n), codes("ar", "pt-BR"), MODEL)
    )

    assert receipt.ok
    arabic = read(l10n / "app_ar.arb")
    assert list(arabic) == ["@@locale", "@@x-reviewed", "appTitle", "greeting", "noteCount", "role"]
    assert arabic["@@locale"] == "ar"
    assert arabic["greeting"] == "[ar] Hello {name}!"
    assert read(l10n / "app_pt_BR.arb")["@@locale"] == "pt_BR"
    notes = {str(unit.path): unit.note for batch in gateway.batches for unit in batch.units}
    assert notes["greeting"] == "Shown on the home screen"
    assert notes["noteCount"] is None


async def test_a_django_tree_is_filled_and_extended(
    mediator: Mediator, examples: Path, gateway: FakeGateway
) -> None:
    locale = examples / "django" / "locale"

    receipt = await mediator.send(
        GenerateLocalesCommand(TreeRequest(locale), codes("fr", "ar"), MODEL)
    )

    assert receipt.ok
    french = (locale / "fr/LC_MESSAGES/django.po").read_text(encoding="utf-8")
    assert 'msgstr "Bienvenue dans notre boutique"' in french  # kept
    assert 'msgid "Add"\nmsgstr "[fr] Add"' in french
    assert '"Plural-Forms: nplurals=2; plural=(n > 1);\\n"' in french  # its own
    assert 'msgstr[1] "[fr] Hello %(name)s, you have %(count)d new messages."\n\n' in french
    assert "fuzzy" not in french
    assert '"Last-Translator: Camille <camille@example.com>\\n"' in french
    arabic = (locale / "ar/LC_MESSAGES/django.po").read_text(encoding="utf-8")
    assert "French" not in arabic
    assert '"Language: ar\\n"' in arabic
    assert 'msgstr[5] "[ar] Hello' in arabic
    notes = {str(unit.path): unit.note for batch in gateway.batches for unit in batch.units}
    assert notes["Add"] == "Translators: the button that adds a product to the cart"
    assert notes[str(KeyPath(("month name\x04May",)))] == "context: month name"


async def test_a_gettext_template_gives_the_catalogs(mediator: Mediator, examples: Path) -> None:
    po = examples / "gnu" / "po"

    receipt = await mediator.send(GenerateLocalesCommand(TreeRequest(po), codes("de", "ja"), MODEL))

    assert receipt.ok
    german = (po / "de.po").read_text(encoding="utf-8")
    assert 'msgstr "Unbenannte Notiz"' in german
    assert 'msgid "Quit"\nmsgstr "[de] Quit"' in german
    japanese = (po / "ja.po").read_text(encoding="utf-8")
    assert japanese.startswith("# The notes app's messages.")
    assert '"Plural-Forms: nplurals=1; plural=(0);\\n"' in japanese
    assert 'msgstr[0] "[ja] %d notes"\n\n' in japanese


async def test_an_angular_template_gives_the_translations(
    mediator: Mediator, examples: Path, gateway: FakeGateway
) -> None:
    locale = examples / "angular" / "src" / "locale"

    receipt = await mediator.send(
        GenerateLocalesCommand(TreeRequest(locale / "messages.xlf"), codes("fr", "ar"), MODEL)
    )

    assert receipt.ok
    french = (locale / "messages.fr.xlf").read_text(encoding="utf-8")
    assert "<target>Bonjour i18n !</target>" in french  # kept as it was
    assert '<target>Vous avez <x id="START_BOLD_TEXT"' in french  # its tags moved
    assert '<trans-unit id="minutes" datatype="html">' in french  # added
    arabic = (locale / "messages.ar.xlf").read_text(encoding="utf-8")
    assert 'target-language="ar"' in arabic
    assert (
        REVIEW + "[ar] Welcome back, "
        '<x id="INTERPOLATION" equiv-text="{{ user.name }}"/>! You have '
        '<x id="START_BOLD_TEXT" ctype="x-b" equiv-text="&lt;b&gt;"/>new mail'
    ) in arabic
    assert '<context context-type="linenumber">10</context>' in arabic
    notes = {str(unit.path): unit.note for batch in gateway.batches for unit in batch.units}
    assert notes["greeting"] == "tags: <x1/> is {{ user.name }}, <x2/> is <b>, <x3/> is </b>"
    assert notes["introductionHeader"] == (
        "description: An introduction header for this sample; meaning: User welcome"
    )


async def test_a_symfony_locale_holds_its_text_in_its_targets(
    mediator: Mediator, examples: Path, gateway: FakeGateway
) -> None:
    translations = examples / "symfony" / "translations"

    receipt = await mediator.send(
        GenerateLocalesCommand(
            TreeRequest(translations / "messages+intl-icu.en.xlf"), codes("de"), MODEL
        )
    )

    assert receipt.ok
    german = (translations / "messages+intl-icu.de.xlf").read_text(encoding="utf-8")
    assert german.startswith('<?xml version="1.0" encoding="UTF-8"?>\n<xliff')
    assert 'target-language="de"' in german
    assert ("<source>cart.empty</source>\n        " + REVIEW + "[de] Your cart is empty.") in german
    notes = {str(unit.path): unit.note for batch in gateway.batches for unit in batch.units}
    assert notes["Bt8LvVd"] == "key: cart.empty"


def laravel(path: Path) -> TreeRequest:
    return TreeRequest(path, syntax=MessageSyntax.LARAVEL)


async def test_a_laravel_tree_is_generated_from_its_keys(examples: Path) -> None:
    gateway = FakeGateway(broken_first={'["Welcome, :name!"]'})
    container = build_container(build_mediator(), Console(quiet=True), FakeModel(gateway))
    async with container() as request:
        mediator = await request.get(Mediator)
        lang = examples / "laravel" / "lang"
        receipt = await mediator.send(GenerateLocalesCommand(laravel(lang), codes("de"), MODEL))
    await container.close()

    (result,) = receipt.results
    assert result.status == ResultStatus.WRITTEN, result
    german = read(lang / "de.json")
    assert list(german) == list(read(lang / "fr.json"))
    assert german["Welcome, :name!"] == "[de] Welcome, :name!"
    retried = [batch for batch in gateway.batches if batch.problems]
    assert "missing :name" in next(iter(retried[0].problems.values()))[0]


async def test_a_laravel_tree_with_its_source_takes_the_target_s_forms(
    mediator: Mediator, examples: Path
) -> None:
    lang = examples / "laravel" / "lang"
    (lang / "en.json").write_text(
        json.dumps({"apples": "One apple|:count apples", "o": "{0} None|[1,*] :count orders"})
    )

    receipt = await mediator.send(GenerateLocalesCommand(laravel(lang), codes("ru"), MODEL))

    (result,) = receipt.results
    assert result.status == ResultStatus.WRITTEN, result
    russian = read(lang / "ru.json")
    assert russian["apples"].count("|") == 2
    assert russian["o"] == "{0}[ru] None|[1,*][ru] :count orders"
    assert "fr.json" not in str(result.path)


async def generate(
    gateway: FakeGateway, tree: TreeRequest, *targets: str, **options: object
) -> list:  # type: ignore[type-arg]
    container = build_container(build_mediator(), Console(quiet=True), FakeModel(gateway))
    async with container() as request:
        mediator = await request.get(Mediator)
        receipt = await mediator.send(
            GenerateLocalesCommand(
                tree, codes(*targets), MODEL, GenerationOptions(max_attempts=2, **options)
            )
        )
    await container.close()
    return list(receipt.results)


async def test_a_fallback_is_recorded_beside_the_targets(examples: Path) -> None:
    locales = examples / "i18next" / "locales"
    tree = TreeRequest(locales / "en", include=("common.json",))

    await generate(Stubborn(), tree, "it")

    assert read(locales / ".i18n-ai-fallbacks.json") == {
        "version": 1,
        "fallbacks": [
            {
                "file": "it/common.json",
                "path": ["app", "welcome"],
                "problems": [{"rule": "placeholders", "message": "missing {{name}}"}],
                "rejected": "[it] Welcome back, !",
            }
        ],
    }


async def test_a_recorded_fallback_is_translated_again(examples: Path) -> None:
    locales = examples / "i18next" / "locales"
    tree = TreeRequest(locales / "en", include=("common.json",))
    await generate(Stubborn(), tree, "it")

    gateway = FakeGateway()
    (result,) = await generate(gateway, tree, "it")

    sent = [str(unit.path) for batch in gateway.batches for unit in batch.units]
    assert sent == ["app.welcome"]
    assert result.translated == 1
    assert read(locales / "it" / "common.json")["app"]["welcome"] == "[it] Welcome back, {{name}}!"
    assert not (locales / ".i18n-ai-fallbacks.json").exists()


async def test_a_run_without_fallbacks_writes_no_record(examples: Path) -> None:
    locales = examples / "i18next" / "locales"

    await generate(FakeGateway(), TreeRequest(locales / "en", include=("common.json",)), "it")

    assert not (locales / ".i18n-ai-fallbacks.json").exists()


async def test_a_run_keeps_the_entries_it_did_not_write(examples: Path) -> None:
    locales = examples / "i18next" / "locales"
    tree = TreeRequest(locales / "en", include=("common.json",))
    await generate(Stubborn(), tree, "it", "de")

    await generate(FakeGateway(), tree, "it")

    files = [entry["file"] for entry in read(locales / ".i18n-ai-fallbacks.json")["fallbacks"]]
    assert files == ["de/common.json"]


class Unreachable(FakeGateway):
    async def translate(self, batch):  # type: ignore[no-untyped-def]
        raise ConnectionError("the model is unreachable")


async def test_a_refused_or_failed_file_leaves_the_record_as_it_was(examples: Path) -> None:
    locales = examples / "i18next" / "locales"
    tree = TreeRequest(locales / "en", include=("common.json",))
    await generate(Stubborn(), tree, "it")
    before = read(locales / ".i18n-ai-fallbacks.json")

    (refused,) = await generate(Stubborn(), tree, "it", strict=True)
    (failed,) = await generate(Unreachable(), tree, "it")

    assert (refused.status, failed.status) == (ResultStatus.REFUSED, ResultStatus.FAILED)
    assert read(locales / ".i18n-ai-fallbacks.json") == before


async def test_a_bundle_s_record_names_its_locale(examples: Path) -> None:
    bundle = examples / "bundle" / "i18n.json"
    await generate(Stubborn("%{name}"), TreeRequest(bundle), "fr")

    (entry,) = read(examples / "bundle" / ".i18n-ai-fallbacks.json")["fallbacks"]
    assert (entry["file"], entry["key"], entry["path"]) == ("i18n.json", "fr", ["greeting"])

    await generate(FakeGateway(), TreeRequest(bundle), "fr")

    assert read(bundle)["fr"]["greeting"] == "[fr] Hello, %{name}!"
    assert not (examples / "bundle" / ".i18n-ai-fallbacks.json").exists()


async def test_a_laravel_fallback_is_translated_again_from_its_key(examples: Path) -> None:
    lang = examples / "laravel" / "lang"
    await generate(Stubborn(":name"), laravel(lang), "de")
    assert read(lang / "de.json")["Welcome, :name!"] == "Welcome, :name!"

    await generate(FakeGateway(), laravel(lang), "de")

    assert read(lang / "de.json")["Welcome, :name!"] == "[de] Welcome, :name!"
    assert not (lang / ".i18n-ai-fallbacks.json").exists()
