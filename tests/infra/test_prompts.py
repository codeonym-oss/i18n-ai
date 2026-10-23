import json

from i18n_ai.domain.exports.locale import (
    KeyPath,
    LocaleCode,
    LocaleDocument,
    MessageSyntax,
    extract_schema,
)
from i18n_ai.infra.adapters.langgraph.prompts import (
    classify_human,
    classify_system,
    translate_human,
    translate_system,
)

ICU = LocaleDocument(
    {
        "unread": "You have {count, plural, =0 {nothing} one {# message} other {# messages}}.",
        "invite": "Join <b>{team}</b>",
    }
)
I18NEXT = LocaleDocument({"item_one": "{{count}} item", "item_other": "{{count}} items"})


def test_the_rules_follow_the_file_and_the_target() -> None:
    schema = extract_schema(ICU, LocaleCode("en"), LocaleCode("ar"))

    prompt = translate_system(schema, "messages.json", "the inbox", "A mail client")

    assert "from English (en) into Arabic (ar)" in prompt
    assert "The website: A mail client" in prompt
    assert "for the inbox." in prompt
    assert "zero, one, two, few, many, other" in prompt  # Arabic's plural categories
    assert "ICU MessageFormat" in prompt
    assert "tags" in prompt
    assert "right to left" in prompt


def test_a_plural_family_is_explained() -> None:
    schema = extract_schema(I18NEXT, LocaleCode("en"), LocaleCode("ja"))

    prompt = translate_system(schema, "common.json", None, None)

    assert "`{{name}}` interpolations" in prompt
    assert "show the count with the source's count placeholder" in prompt
    assert "ICU MessageFormat" not in prompt
    assert "right to left" not in prompt


def test_a_retry_carries_the_previous_answer_and_its_problems() -> None:
    schema = extract_schema(I18NEXT, LocaleCode("en"), LocaleCode("ru"))
    unit = schema.units[0]

    prompt = translate_human(
        schema.units, {unit.id: "предмет"}, {unit.id: ["missing {{count}}"]}, schema.target
    )

    assert prompt.startswith("Your previous translations")
    sent = json.loads(prompt.split("```json\n")[1].split("\n```")[0])
    first = next(message for message in sent if message["id"] == unit.id)
    assert first["your_previous_translation"] == "предмет"
    assert first["problems_to_fix"] == ["missing {{count}}"]
    assert first["placeholders"] == ["{{count}}"]
    assert "plural" in first


def test_a_note_is_sent_with_its_message() -> None:
    document = LocaleDocument(
        {"save": "Save", "open": "Open"},
        notes={KeyPath(("save",)): "Button that saves the profile"},
    )
    schema = extract_schema(document, LocaleCode("en"), LocaleCode("fr"))

    system = translate_system(schema, "app_en.arb", None, None)
    sent = json.loads(
        translate_human(schema.units, {}, {}, schema.target).split("```json\n")[1].split("\n```")[0]
    )

    assert "`note`" in system
    assert sent[0]["note"] == "Button that saves the profile"
    assert "note" not in sent[1]
    assert "`note`" not in translate_system(
        extract_schema(I18NEXT, LocaleCode("en"), LocaleCode("fr")), "a.json", None, None
    )


def test_the_classifier_sees_the_file() -> None:
    assert "English" in classify_system(LocaleCode("en"))
    assert "`meta.json`" in classify_human("meta.json", '{"version": 2}')


def test_laravel_s_placeholders_are_explained_in_its_syntax_only() -> None:
    document = LocaleDocument({"Welcome, :name!": "Welcome, :name!"})
    en, de = LocaleCode("en"), LocaleCode("de")

    prompt = translate_system(
        extract_schema(document, en, de, MessageSyntax.LARAVEL), "", None, None
    )

    assert "`:name` placeholders" in prompt
    assert "`:Name` capitalized" in prompt
    assert ":Name" not in translate_system(extract_schema(document, en, de), "", None, None)


def sent(schema) -> list[dict]:  # type: ignore[no-untyped-def,type-arg]
    return json.loads(
        translate_human(schema.units, {}, {}, schema.target).split("```json\n")[1].split("\n```")[0]
    )


def test_a_pipe_plural_is_sent_with_the_target_s_forms() -> None:
    document = LocaleDocument({"apples": ":count apple|:count apples", "o": "{0} none|[1,*] some"})
    en = LocaleCode("en")

    russian = extract_schema(document, en, LocaleCode("ru"), MessageSyntax.LARAVEL)
    apples, orders = sent(russian)

    assert apples["pipe_forms"] == [
        "1, 21, 31, 41, 51, 61, …",
        "2, 3, 4, 22, 23, 24, …",
        "0, 5, 6, 7, 8, 9, …",
    ]
    assert "keep_ranges" not in apples
    assert orders["keep_ranges"] == ["{0}", "[1,*]"]
    assert "pipe_forms" not in orders
    assert "pipe plural" in translate_system(russian, "", None, None)

    japanese = extract_schema(document, en, LocaleCode("ja"), MessageSyntax.LARAVEL)
    assert sent(japanese)[0]["pipe_forms"] == ["every count"]
    assert "pipe plural" not in translate_system(
        extract_schema(document, en, LocaleCode("ru")), "", None, None
    )
