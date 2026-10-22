import pytest

from i18n_ai.domain.exports.locale import (
    LocaleCode,
    LocaleDocument,
    MissingTranslations,
    extract_schema,
)

DOCUMENT = LocaleDocument(
    {
        "title": "Cart",
        "item_one": "one item",
        "item_other": "{{count}} items",
        "place_ordinal_one": "{{count}}st",
        "place_ordinal_two": "{{count}}nd",
        "place_ordinal_few": "{{count}}rd",
        "place_ordinal_other": "{{count}}th",
        "limit": 5,
        "blank": "",
        "list": ["a", "b"],
        "option_other": "Other",
    }
)


def keys(locale: str) -> list[str]:
    schema = extract_schema(DOCUMENT, LocaleCode("en"), LocaleCode(locale))
    return list(schema.template)


def test_a_plural_family_takes_the_targets_categories() -> None:
    assert keys("ar")[:7] == [
        "title",
        "item_zero",
        "item_one",
        "item_two",
        "item_few",
        "item_many",
        "item_other",
    ]
    assert [key for key in keys("ja") if key.startswith("item_")] == ["item_other"]


def test_ordinal_families_take_the_ordinal_categories() -> None:
    assert [key for key in keys("fr") if key.startswith("place_")] == [
        "place_ordinal_one",
        "place_ordinal_other",
    ]


def test_a_lone_other_key_is_not_a_family() -> None:
    assert "option_other" in keys("ja")


def test_a_missing_form_is_translated_from_other() -> None:
    schema = extract_schema(DOCUMENT, LocaleCode("en"), LocaleCode("ru"))
    few = next(unit for unit in schema.units if str(unit.path) == "item_few")
    assert few.source == "{{count}} items"
    assert few.plural is not None
    assert few.plural.source_category == "other"


def test_render_keeps_order_and_non_text() -> None:
    schema = extract_schema(DOCUMENT, LocaleCode("en"), LocaleCode("fr"))
    rendered = schema.render({unit.id: unit.source.upper() for unit in schema.units})
    assert rendered["limit"] == 5
    assert rendered["blank"] == ""
    assert rendered["list"] == ["A", "B"]
    assert next(iter(rendered)) == "title"


def test_render_refuses_a_missing_unit() -> None:
    schema = extract_schema(DOCUMENT, LocaleCode("en"), LocaleCode("fr"))
    with pytest.raises(MissingTranslations):
        schema.render({})
