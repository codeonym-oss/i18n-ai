"""gettext's `Plural-Forms`, read for which CLDR category each form is for."""

import pytest

from i18n_ai.domain.exports.locale import LocaleCode
from i18n_ai.infra.adapters.filesystem.formats.plural_forms import numbering


@pytest.mark.parametrize(
    ("locale", "header", "forms"),
    [
        ("de", "nplurals=2; plural=(n != 1);", ("one", "other")),
        ("fr", "nplurals=2; plural=(n > 1);", ("one", "other")),
        ("ja", "nplurals=1; plural=0;", ("other",)),
        (
            "ru",
            "nplurals=3; plural=(n%10==1 && n%100!=11 ? 0 : n%10>=2 && n%10<=4 && "
            "(n%100<10 || n%100>=20) ? 1 : 2);",
            ("one", "few", "many"),
        ),
        (
            "ar",
            "nplurals=6; plural=(n==0 ? 0 : n==1 ? 1 : n==2 ? 2 : n%100>=3 && n%100<=10 ? 3 "
            ": n%100>=11 ? 4 : 5);",
            ("zero", "one", "two", "few", "many", "other"),
        ),
    ],
)
def test_a_header_numbers_the_categories(locale: str, header: str, forms: tuple[str, ...]) -> None:
    assert numbering(header, LocaleCode(locale)) == forms


@pytest.mark.parametrize("locale", ["ar", "ru", "fr", "pt-BR", "ja", "cy", "lt", "he"])
def test_cldr_numbers_its_own_categories(locale: str) -> None:
    code = LocaleCode(locale)

    assert numbering(code.gettext_plural_forms(), code) == code.plural_categories()


@pytest.mark.parametrize(
    "header",
    [
        "nplurals=INTEGER; plural=EXPRESSION;",  # a template's
        "nplurals=2; plural=(n > 1 ? 2 : 0);",  # a form it does not have
        "nplurals=2; plural=(n / 0);",
        "nplurals=2; plural=(n > );",
        "",
    ],
)
def test_an_unreadable_header_numbers_nothing(header: str) -> None:
    assert numbering(header, LocaleCode("fr")) is None
