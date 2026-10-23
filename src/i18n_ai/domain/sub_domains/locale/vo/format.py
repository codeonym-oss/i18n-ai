from enum import StrEnum


class LocaleFormat(StrEnum):
    """The file format a tree's locales are written in.

    - `json`: `.json`, for i18next, next-intl, vue-i18n, ngx-translate...
    - `yaml`: `.yml` and `.yaml`, for Rails, vue-i18n, Symfony, Hugo..."""

    JSON = "json"
    YAML = "yaml"
