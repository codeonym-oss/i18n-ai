from i18n_ai.domain.exports.locale import (
    LocaleCode,
    LocaleDocument,
    Severity,
    ViolationCode,
    check,
    extract_schema,
    normalize,
    reusable_translations,
)


def schema_of(content: dict[str, object], target: str = "fr"):  # type: ignore[no-untyped-def]
    return extract_schema(LocaleDocument(content), LocaleCode("en"), LocaleCode(target))


def codes(violations) -> list[ViolationCode]:  # type: ignore[no-untyped-def]
    return [violation.code for violation in violations]


def test_a_lost_placeholder_is_refused() -> None:
    schema = schema_of({"m": "Hi {{name}}"})
    assert codes(check(schema, schema.units[0], "Salut")) == [ViolationCode.PLACEHOLDERS]


def test_a_moved_placeholder_is_fine() -> None:
    schema = schema_of({"m": "{{n}} of {{total}}"})
    assert check(schema, schema.units[0], "sur {{total}}, {{n}}") == []


def test_a_plural_form_may_show_the_count_or_not() -> None:
    schema = schema_of({"x_one": "one file", "x_other": "{{count}} files"}, "ru")
    one = next(unit for unit in schema.units if str(unit.path) == "x_one")
    assert check(schema, one, "{{count}} файл") == []


def test_icu_must_keep_explicit_selectors() -> None:
    schema = schema_of({"m": "{n, plural, =0 {none} one {# file} other {# files}}"})
    found = check(schema, schema.units[0], "{n, plural, one {# fichier} other {# fichiers}}")
    assert ViolationCode.PLURAL_SELECTORS in codes(found)


def test_icu_with_the_wrong_categories_is_a_warning() -> None:
    schema = schema_of({"m": "{n, plural, one {# file} other {# files}}"}, "ru")
    found = check(schema, schema.units[0], "{n, plural, one {# файл} other {# файлов}}")
    assert [violation.severity for violation in found] == [Severity.WARNING]


def test_a_select_keeps_its_options() -> None:
    schema = schema_of({"m": "{g, select, male {He} female {She} other {They}}"})
    found = check(schema, schema.units[0], "{g, select, homme {Il} other {Iel}}")
    assert ViolationCode.SELECT_OPTIONS in codes(found)


def test_an_apostrophe_that_quotes_icu_is_explained() -> None:
    schema = schema_of({"m": "{n, number} of {total}"})
    (violation,) = check(schema, schema.units[0], "{n, number} sur l'{total}")
    assert "apostrophe" in violation.message


def test_an_untranslated_message_is_a_warning() -> None:
    schema = schema_of({"m": "Settings"})
    (violation,) = check(schema, schema.units[0], "Settings")
    assert violation.code == ViolationCode.UNCHANGED
    assert violation.severity == Severity.WARNING


def test_whitespace_at_the_edges_is_restored() -> None:
    schema = schema_of({"m": "  Total: "})
    assert normalize(schema.units[0], "Total :") == "  Total : "


def test_only_good_existing_translations_are_reused() -> None:
    schema = schema_of({"a": "Hi {{name}}", "b": "Bye", "c": "Later"})
    existing = LocaleDocument({"a": "Salut {{nom}}", "b": "Au revoir"})
    assert reusable_translations(schema, existing) == {"2": "Au revoir"}
