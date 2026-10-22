import pytest

from i18n_ai.domain.exports.locale import (
    IcuSyntaxError,
    PlaceholderStyle,
    detect_styles,
    signature_of,
)
from i18n_ai.domain.sub_domains.locale.placeholders import icu


def test_double_braces_are_normalized() -> None:
    assert signature_of("Hi {{ name }}", quotes=False).tokens == ("{{name}}",)


def test_every_family_of_placeholder_is_found() -> None:
    text = "%{user} sent %d files to %(team)s: <b>$t(common.ok)</b> @:app.name <0/>"
    tokens = signature_of(text, quotes=False).tokens
    assert set(tokens) == {
        "%{user}",
        "%d",
        "%(team)s",
        "<b>",
        "</b>",
        "$t(common.ok)",
        "@:app.name",
        "<0/>",
    }


def test_a_percent_sign_in_prose_is_not_printf() -> None:
    assert signature_of("50% off everything", quotes=False).tokens == ()


def test_icu_plural_branches_are_one_branching() -> None:
    signature = signature_of(
        "{n, plural, =0 {none} one {# file of {owner}} other {# files of {owner}}}", quotes=True
    )
    assert signature.tokens == ("{n, plural}",)
    (branching,) = signature.branchings
    assert branching.selectors == {"=0", "one", "other"}
    assert branching.inner == {"{owner}"}


def test_icu_quotes_hide_an_argument() -> None:
    assert signature_of("l'{count}", quotes=True).tokens == ()
    assert signature_of("l'{count}", quotes=False).tokens == ("{count}",)


def test_a_plural_without_other_is_broken() -> None:
    with pytest.raises(IcuSyntaxError):
        icu.parse("{n, plural, one {x}}", quotes=True)


def test_unbalanced_braces_count_as_placeholders() -> None:
    signature = signature_of("oops {", quotes=False)
    assert signature.error is not None
    assert signature.tokens == ("{",)


def test_styles_are_detected() -> None:
    styles = detect_styles(["Hi {{name}}", "{n, plural, other {#}}", "<b>x</b>"])
    assert styles == {PlaceholderStyle.DOUBLE_BRACES, PlaceholderStyle.ICU, PlaceholderStyle.TAGS}
