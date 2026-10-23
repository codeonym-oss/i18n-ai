from i18n_ai.domain.exports.locale import (
    LocaleCode,
    LocaleDocument,
    MessageSyntax,
    Severity,
    ViolationCode,
    check,
    extract_schema,
    normalize,
    reusable_translations,
)


def schema_of(  # type: ignore[no-untyped-def]
    content: dict[str, object],
    target: str = "fr",
    syntax: MessageSyntax = MessageSyntax.STANDARD,
):
    return extract_schema(LocaleDocument(content), LocaleCode("en"), LocaleCode(target), syntax)


def laravel(text: str, target: str = "fr"):  # type: ignore[no-untyped-def]
    schema = schema_of({text: text}, target, MessageSyntax.LARAVEL)
    return schema, schema.units[0]


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

    schema = schema_of({"x": {"one": "1 file", "other": "%{count} files"}}, "ru")
    one = next(unit for unit in schema.units if str(unit.path) == "x.one")
    assert check(schema, one, "%{count} файл") == []


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


def test_a_laravel_placeholder_keeps_its_name() -> None:
    schema, unit = laravel("Welcome, :name! You have :count messages")
    assert schema.syntax == MessageSyntax.LARAVEL
    assert check(schema, unit, ":Name, bienvenue ! Vous avez :count messages") == []
    for broken in (
        "Bienvenue ! Vous avez :count messages",
        "Bienvenue, :nom ! Vous avez :count messages",
        "Bienvenue, :name :name ! Vous avez :count messages",
    ):
        assert codes(check(schema, unit, broken)) == [ViolationCode.PLACEHOLDERS], broken


def test_a_colon_is_text_outside_laravel_s_syntax() -> None:
    schema = schema_of({"m": "Ratio:high, :name"})
    assert check(schema, schema.units[0], "Verhältnis:hoch, :nom") == []


def test_a_pipe_plural_takes_the_target_s_number_of_forms() -> None:
    schema, unit = laravel(":count apple|:count apples", "ru")
    assert check(schema, unit, ":count яблоко|:count яблока|:count яблок") == []
    assert codes(check(schema, unit, ":count яблоко|:count яблок")) == [ViolationCode.PIPE_FORMS]
    assert codes(check(schema, unit, ":count яблок")) == [ViolationCode.PIPE_FORMS]

    schema, unit = laravel(":count apple|:count apples", "ja")
    assert check(schema, unit, "りんご:count個") == []
    schema, unit = laravel(":count apple|:count apples", "fr")
    assert check(schema, unit, ":count pomme|:count pommes") == []


def test_a_pipe_plural_keeps_its_ranges() -> None:
    schema, unit = laravel("{0} No orders|[1,*] :count orders", "ru")
    assert check(schema, unit, "{0} Нет заказов|[1,*] :count заказов") == []
    for broken in ("{0} Нет заказов|[2,*] :count заказов", "{0} Нет заказов"):
        assert ViolationCode.PIPE_RANGES in codes(check(schema, unit, broken)), broken


def test_a_pipe_plural_s_placeholders_are_a_set() -> None:
    schema, unit = laravel(":name has :count apple|:name has :count apples", "ru")
    assert check(schema, unit, "У :name :count яблоко|:count яблока|:count яблок") == []
    found = check(schema, unit, "У :name :count яблоко|:city яблока|:count яблок")
    assert codes(found) == [ViolationCode.PLACEHOLDERS]
    assert "unexpected :city" in found[0].message


def test_a_spaced_pipe_is_text() -> None:
    schema, unit = laravel("Dashboard | Acme", "ru")
    assert check(schema, unit, "Панель | Acme") == []


def test_a_pipe_plural_s_forms_have_no_space_around_their_pipes() -> None:
    schema, unit = laravel("apple|apples")
    found = check(schema, unit, "une pomme | des pommes")
    assert codes(found) == [ViolationCode.PIPE_FORMS]
    assert "no space" in found[0].message
