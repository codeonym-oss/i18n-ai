import json

from i18n_ai.domain.exports.locale import KeyPath, LocaleCode, LocaleDocument, extract_schema
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

    prompt = translate_human(schema.units, {unit.id: "предмет"}, {unit.id: ["missing {{count}}"]})

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
    sent = json.loads(translate_human(schema.units, {}, {}).split("```json\n")[1].split("\n```")[0])

    assert "`note`" in system
    assert sent[0]["note"] == "Button that saves the profile"
    assert "note" not in sent[1]
    assert "`note`" not in translate_system(
        extract_schema(I18NEXT, LocaleCode("en"), LocaleCode("fr")), "a.json", None, None
    )


def test_the_classifier_sees_the_file() -> None:
    assert "English" in classify_system(LocaleCode("en"))
    assert "`meta.json`" in classify_human("meta.json", '{"version": 2}')
