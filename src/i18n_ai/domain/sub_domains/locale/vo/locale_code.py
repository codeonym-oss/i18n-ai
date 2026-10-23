import re
from dataclasses import dataclass
from functools import cached_property
from typing import Literal

from babel import Locale, UnknownLocaleError
from babel.plural import to_gettext

from ..exceptions.locale_code import InvalidLocaleCode

_PATTERN = re.compile(r"^[A-Za-z]{2,3}(?:[-_][A-Za-z0-9]{2,8})*$")

PluralKind = Literal["cardinal", "ordinal"]
CARDINAL: PluralKind = "cardinal"
ORDINAL: PluralKind = "ordinal"

# CLDR's order of the plural categories; `other` is always last, and always there.
_CATEGORY_ORDER = ("zero", "one", "two", "few", "many", "other")


@dataclass(frozen=True)
class LocaleCode:
    """A locale, as a tree names it: `en`, `pt-BR`, `zh_Hant`. It keeps the spelling it was
    given, as it names directories and files; two codes are the same locale when they only
    differ in case or separator (`pt-BR`, `pt_br`)."""

    value: str

    def __post_init__(self) -> None:
        value = self.value.strip()
        if not _PATTERN.match(value):
            raise InvalidLocaleCode(self.value)
        object.__setattr__(self, "value", value)

    @classmethod
    def recognized(cls, name: str) -> "LocaleCode | None":
        """The locale `name` spells, if CLDR knows it; None for names such as `common` or `app`,
        which are not locales though they could look like one."""
        if not _PATTERN.match(name):
            return None
        code = cls(name)
        return code if code._cldr is not None else None

    @property
    def key(self) -> str:
        """The comparable form: lower case, `_` as the separator."""
        return self.value.replace("-", "_").lower()

    @property
    def language(self) -> str:
        return self.key.split("_", 1)[0]

    def same_as(self, other: "LocaleCode") -> bool:
        return self.key == other.key

    @cached_property
    def _cldr(self) -> Locale | None:
        for candidate in (self.value.replace("-", "_"), self.language):
            try:
                return Locale.parse(candidate)
            except (UnknownLocaleError, ValueError, TypeError):
                continue
        return None

    @property
    def display_name(self) -> str:
        """The locale's English name, such as `Portuguese (Brazil)`; the code when CLDR does not
        know it."""
        if self._cldr is None:
            return self.value
        return str(self._cldr.get_display_name("en") or self.value)

    @property
    def direction(self) -> str:
        """`ltr` or `rtl`."""
        return str(self._cldr.text_direction) if self._cldr is not None else "ltr"

    def plural_categories(self, kind: PluralKind = CARDINAL) -> tuple[str, ...]:
        """The CLDR plural categories this locale's messages need, in CLDR's order, `other`
        always included: `('one', 'other')` for English, all six for Arabic."""
        if self._cldr is None:
            return ("one", "other")
        form = self._cldr.ordinal_form if kind == ORDINAL else self._cldr.plural_form
        tags = set(form.tags) | {"other"}
        return tuple(category for category in _CATEGORY_ORDER if category in tags)

    def plural_category(self, count: int) -> str:
        """The CLDR cardinal category of a whole `count`: Russian's `few` for 3."""
        return (
            str(self._cldr.plural_form(count))
            if self._cldr is not None
            else ("one" if count == 1 else "other")
        )

    def gettext_plural_forms(self) -> str:
        """gettext's `Plural-Forms` for this locale, numbering its cardinal categories in CLDR's
        order: `nplurals=2; plural=(n != 1);` in spirit for English. gettext counts are integers
        written plainly, so CLDR's exponent operand `e` is 0."""
        if self._cldr is None:
            return "nplurals=2; plural=(n != 1);"
        return re.sub(r"\be\b", "0", to_gettext(self._cldr.plural_form))

    def __str__(self) -> str:
        return self.value
