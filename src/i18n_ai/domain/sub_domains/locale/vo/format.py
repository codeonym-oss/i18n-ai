from enum import StrEnum


class LocaleFormat(StrEnum):
    """The file format a tree's locales are written in.

    - `json`: `.json`, for i18next, next-intl, vue-i18n, ngx-translate...
    - `yaml`: `.yml` and `.yaml`, for Rails, vue-i18n, Symfony, Hugo...
    - `arb`: `.arb`, Flutter's Application Resource Bundle"""

    JSON = "json"
    YAML = "yaml"
    ARB = "arb"

    @property
    def locale_separator(self) -> str:
        """How a new locale is spelled in this format's file names: Flutter's `app_pt_BR.arb`."""
        return "_" if self is LocaleFormat.ARB else "-"
