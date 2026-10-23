from functools import cache

from babel import localedata

from .locale_code import LocaleCode

# The locales websites ship most, first; then every other language CLDR knows, by name.
_POPULAR = (
    "es", "fr", "de", "pt-BR", "it", "ja", "zh-Hans", "ko", "ar", "ru", "nl", "tr", "pl", "hi",
    "id", "vi", "th", "sv", "uk", "he", "pt-PT", "zh-Hant", "cs", "da", "fi", "nb", "el", "ro",
    "hu", "bn", "fa", "ms", "ur", "en-GB", "es-MX", "es-419", "fr-CA", "de-CH", "zh-TW", "zh-HK",
)  # fmt: skip


@cache
def known_locales() -> tuple[LocaleCode, ...]:
    """The locales to pick targets from: the most shipped ones first, then every language CLDR
    knows, by English name."""
    popular = [LocaleCode(code) for code in _POPULAR]
    taken = {locale.key for locale in popular}
    rest = [
        locale
        for identifier in localedata.locale_identifiers()
        if "_" not in identifier and identifier != "root"
        if (locale := LocaleCode.recognized(identifier)) is not None and locale.key not in taken
    ]
    rest.sort(key=lambda locale: locale.display_name.casefold())
    return (*popular, *rest)
