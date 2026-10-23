"""Laravel's pipe plurals: which messages are ones, their forms, and how many forms each
language takes, by Laravel's own table."""

import pytest

from i18n_ai.domain.exports.locale import (
    LocaleCode,
    MessageSyntax,
    PipePlural,
    PlaceholderStyle,
    detect_styles,
    laravel_forms,
    signature_of,
)


def pipes(text: str) -> PipePlural | None:
    return signature_of(text, quotes=False, syntax=MessageSyntax.LARAVEL).pipes


@pytest.mark.parametrize(
    ("locale", "count"),
    [("en", 2), ("fr", 2), ("ru", 3), ("ja", 1), ("ar", 6), ("cy", 4), ("pt-BR", 2), ("xx", 1)],
)
def test_each_language_takes_laravel_s_number_of_forms(locale: str, count: int) -> None:
    assert len(laravel_forms(LocaleCode(locale))) == count


def test_each_form_is_told_by_the_counts_laravel_sends_to_it() -> None:
    assert laravel_forms(LocaleCode("fr")) == ("0, 1", "2, 3, 4, 5, 6, 7, …")
    assert laravel_forms(LocaleCode("ru")) == (
        "1, 21, 31, 41, 51, 61, …",
        "2, 3, 4, 22, 23, 24, …",
        "0, 5, 6, 7, 8, 9, …",
    )
    assert laravel_forms(LocaleCode("ja")) == ("every count",)


def test_a_pipe_plural_is_its_forms_and_their_ranges() -> None:
    assert pipes("apple|apples") == PipePlural((None, None), ("apple", "apples"))
    assert pipes("{0} none|[1,19] some|[20,*] many") == PipePlural(
        ("{0}", "[1,19]", "[20,*]"), (" none", " some", " many")
    )


# Laravel reads a range at the start of a form only: ` [2,*] many` has none
@pytest.mark.parametrize("text", ["Dashboard | Acme", "a | b | c", "no pipe", "one | [2,*] many"])
def test_a_pipe_with_spaces_around_it_and_no_range_is_text(text: str) -> None:
    assert pipes(text) is None


def test_a_pipe_plural_with_a_range_needs_no_unspaced_pipe() -> None:
    assert pipes("{0} none | [1,*] some") == PipePlural(("{0}", None), (" none ", " [1,*] some"))


def test_a_pipe_plural_s_placeholders_are_its_forms_without_their_ranges() -> None:
    signature = signature_of(
        "{0} :count none|[1,*] :count some", quotes=False, syntax=MessageSyntax.LARAVEL
    )
    assert signature.tokens == (":count", ":count")
    assert signature.error is None


def test_pipes_are_text_outside_laravel_s_syntax() -> None:
    assert signature_of("apple|apples", quotes=False).pipes is None


def test_a_range_is_not_an_icu_argument_of_the_file() -> None:
    texts = ["{0} No orders|[1,*] :count orders"]
    assert detect_styles(texts, MessageSyntax.LARAVEL) == {PlaceholderStyle.LARAVEL}
