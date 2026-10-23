from pathlib import Path, PurePosixPath

import pytest

from i18n_ai.domain.contract.exceptions.generic import EmptyValueProvided
from i18n_ai.domain.exports.locale import (
    ORDINAL,
    IcuSyntaxError,
    InvalidLocaleCode,
    JsonStyle,
    KeyPath,
    LocaleCode,
    LocaleDocument,
    LocaleTree,
    LocaleTreeNotFound,
    SourceFile,
    SourceLocaleUnknown,
    TargetIsSource,
    TreeLayout,
    known_locales,
    qualify,
)
from i18n_ai.domain.exports.provider import (
    ModelSpec,
    ProviderNotInstalled,
    ProviderUnknown,
    ResolvedModel,
)
from i18n_ai.domain.sub_domains.locale.placeholders import icu


@pytest.mark.parametrize("value", ["en", "pt-BR", "pt_br", "zh_Hant", "sr-Latn-RS"])
def test_a_locale_code_keeps_its_spelling(value: str) -> None:
    assert str(LocaleCode(f" {value} ")) == value


@pytest.mark.parametrize("value", ["", "e", "english!", "../en", "en/US"])
def test_a_malformed_locale_code_is_refused(value: str) -> None:
    with pytest.raises(InvalidLocaleCode):
        LocaleCode(value)


def test_codes_differing_in_case_or_separator_are_the_same_locale() -> None:
    assert LocaleCode("pt-BR").same_as(LocaleCode("pt_br"))
    assert LocaleCode("pt-BR").language == "pt"
    assert not LocaleCode("pt-BR").same_as(LocaleCode("pt-PT"))


def test_only_cldr_locales_are_recognized() -> None:
    assert LocaleCode.recognized("fr") == LocaleCode("fr")
    assert LocaleCode.recognized("app") is None
    assert LocaleCode.recognized("common") is None


def test_what_cldr_says_of_a_locale() -> None:
    arabic = LocaleCode("ar")

    assert arabic.display_name == "Arabic"
    assert arabic.direction == "rtl"
    assert arabic.plural_categories() == ("zero", "one", "two", "few", "many", "other")
    assert LocaleCode("ja").plural_categories() == ("other",)
    assert LocaleCode("en").plural_categories(ORDINAL) == ("one", "two", "few", "other")
    assert LocaleCode("pt-BR").display_name == "Portuguese (Brazil)"


def test_a_locale_cldr_does_not_know_falls_back() -> None:
    unknown = LocaleCode("qqx")

    assert unknown.display_name == "qqx"
    assert unknown.direction == "ltr"
    assert unknown.plural_categories() == ("one", "other")


def test_key_paths_read_like_code() -> None:
    path = KeyPath().child("auth").child("errors").child("not.found")

    assert str(path) == 'auth.errors["not.found"]'
    assert str(KeyPath().child("steps").child(2)) == "steps[2]"
    assert str(path.sibling("locked")) == "auth.errors.locked"
    assert str(KeyPath()) == "<root>"


def tree(layout: TreeLayout, root: Path, existing: tuple[str, ...] = ()) -> LocaleTree:
    name = PurePosixPath("auth/login.json" if layout == TreeLayout.DIRECTORY else "en.json")
    file = SourceFile(name, root / "en" / name, LocaleDocument({}, JsonStyle()))
    return LocaleTree(
        root=root,
        layout=layout,
        source=LocaleCode("en"),
        files=(file,),
        existing=tuple(LocaleCode(code) for code in existing),
        output=root,
    )


def test_targets_go_beside_the_source(tmp_path: Path) -> None:
    directory = tree(TreeLayout.DIRECTORY, tmp_path)
    files = tree(TreeLayout.FILE, tmp_path)
    bundle = tree(TreeLayout.BUNDLE, tmp_path / "i18n.json")
    fr = LocaleCode("fr")

    assert directory.target_location(fr, directory.files[0]).path == tmp_path / "fr/auth/login.json"
    assert directory.source_path == tmp_path / "en"
    assert files.target_location(fr, files.files[0]).path == tmp_path / "fr.json"
    location = bundle.target_location(fr, bundle.files[0])
    assert location.path == tmp_path / "i18n.json"
    assert location.bundle_key == "fr"
    assert bundle.source_path == tmp_path / "i18n.json"


def test_an_existing_locale_keeps_its_spelling(tmp_path: Path) -> None:
    directory = tree(TreeLayout.DIRECTORY, tmp_path, existing=("pt_BR",))

    location = directory.target_location(LocaleCode("pt-BR"), directory.files[0])

    assert location.path == tmp_path / "pt_BR/auth/login.json"
    assert directory.has(LocaleCode("pt-br"))


@pytest.mark.parametrize(
    ("content", "qualifies", "reason"),
    [
        ({"title": "Hello", "count": 3}, True, "1 messages"),
        ({"version": 2, "ids": [1, 2, 3], "name": "app"}, False, "looks like data"),
        ({"empty": "", "flag": True}, False, "no text"),
    ],
)
def test_qualification(content: dict[str, object], qualifies: bool, reason: str) -> None:
    result = qualify(LocaleDocument(content, JsonStyle()))

    assert result.qualifies is qualifies
    assert reason in result.reason


def test_a_file_that_is_not_an_object_does_not_qualify() -> None:
    assert qualify(None, "a JSON array").reason == "a JSON array"
    assert not qualify(None).qualifies


@pytest.mark.parametrize(
    "text",
    [
        "{}",
        "{name",
        "{name, number",
        "{name,}",
        "{count, plural, one {#}}",
        "{count, plural, one {#} other {#}",
        "{count, plural, one # other {#}}",
        "{count, plural, {#} other {#}}",
        "{n, number, ::currency/EUR",
    ],
)
def test_broken_icu_is_refused(text: str) -> None:
    with pytest.raises(IcuSyntaxError):
        icu.parse(text, quotes=True)


def test_icu_apostrophes() -> None:
    text, plural = icu.parse("It''s '{literal}' and '#' {n, plural, other {x}}", quotes=True)

    assert isinstance(text, icu.Text)
    assert text.value == "It's {literal} and '#' "  # '#' quotes nothing outside a plural
    assert isinstance(plural, icu.Argument)
    assert plural.type == "plural"


def test_the_refusals_say_what_is_wrong() -> None:
    assert "no locale tree at x: gone" in LocaleTreeNotFound("x", "gone").message
    assert "--source" in SourceLocaleUnknown("x", ["en", "fr"]).message
    assert "has no de locale" in SourceLocaleUnknown("x", ["en"], "de").message
    assert "en is the source" in TargetIsSource("en").message
    assert "nobody" in ProviderUnknown("nobody:m", ["openai"]).message
    assert "langchain-openai" in ProviderNotInstalled("openai", "langchain-openai").message


def test_model_specs() -> None:
    assert str(ModelSpec(" openai:gpt-4.1-mini ")) == "openai:gpt-4.1-mini"
    with pytest.raises(EmptyValueProvided):
        ModelSpec(" ")
    resolved = ResolvedModel("ollama", "qwen2.5:7b", "langchain-ollama", "langchain_ollama")
    assert resolved.spec == "ollama:qwen2.5:7b"


def test_the_known_locales_put_the_most_shipped_first() -> None:
    locales = known_locales()

    assert [locale.value for locale in locales[:3]] == ["es", "fr", "de"]
    assert len({locale.key for locale in locales}) == len(locales)
    assert any(locale.value == "sw" for locale in locales)
    assert not any(locale.value == "en" for locale in locales[:40])
