from enum import StrEnum


class LocaleFormat(StrEnum):
    """The file format a tree's locales are written in.

    - `json`: `.json`, for i18next, next-intl, vue-i18n, ngx-translate...
    - `yaml`: `.yml` and `.yaml`, for Rails, vue-i18n, Symfony, Hugo...
    - `arb`: `.arb`, Flutter's Application Resource Bundle
    - `po`: `.po`, gettext's catalogs, and `.pot`, their templates (Django, WordPress, Babel...)
    - `xliff`: `.xlf` and `.xliff`, XLIFF 1.2 and 2.0 (Angular, Symfony, translation tools)"""

    JSON = "json"
    YAML = "yaml"
    ARB = "arb"
    PO = "po"
    XLIFF = "xliff"

    @property
    def locale_separator(self) -> str:
        """How a new locale is spelled in this format's file names: Flutter's `app_pt_BR.arb`,
        gettext's `pt_BR.po`."""
        return "_" if self in (LocaleFormat.ARB, LocaleFormat.PO) else "-"

    def target_suffix(self, suffix: str) -> str:
        """The extension of a target written from a source file with `suffix`: a gettext
        template's (`.pot`) is a catalog (`.po`)."""
        return ".po" if self is LocaleFormat.PO and suffix.lower() == ".pot" else suffix
