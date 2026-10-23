"""The presets, one row per i18n library. A project may reveal several (a Nuxt app depends on
vue-i18n too): the first row it reveals whose locales are found wins, so the more specific
rows come first."""

from ..placeholders import PlaceholderStyle as Style
from ..vo import LocaleFormat, MessageSyntax
from .preset import ConfigHint, Preset

# A quoted path in JavaScript, TypeScript or JSON: 'locales', "./locales/", `locales`
_QUOTED = r"""['"`]\.?/?([^'"`]+?)/?['"`]"""

PRESETS: tuple[Preset, ...] = (
    # Before the frontend libraries an Inertia app also depends on, whose usual places hold `lang`
    Preset(
        name="laravel",
        library="Laravel",
        example="lang/<lng>.json",
        packages=("laravel/framework",),
        trees=("lang", "resources/lang"),
        format=LocaleFormat.JSON,
        placeholders=(Style.LARAVEL,),
        syntax=MessageSyntax.LARAVEL,
    ),
    Preset(
        name="nuxt-i18n",
        library="Nuxt i18n",
        example="i18n/locales/<lng>.json",
        packages=("@nuxtjs/i18n", "@nuxtjs/i18n-edge"),
        config=(ConfigHint("nuxt.config.*", rf"langDir\s*:\s*{_QUOTED}", ("i18n", "")),),
        trees=("i18n/locales", "locales", "lang"),
        placeholders=(Style.ICU, Style.LINKED, Style.RAILS),
    ),
    Preset(
        name="next-intl",
        library="next-intl",
        example="messages/<lng>.json",
        packages=("next-intl",),
        trees=("messages", "src/messages", "locales"),
        format=LocaleFormat.JSON,
        placeholders=(Style.ICU, Style.TAGS),
    ),
    Preset(
        name="i18next",
        library="i18next, react-i18next, next-i18next",
        example="public/locales/<lng>/<ns>.json",
        packages=("i18next", "react-i18next", "next-i18next"),
        files=("i18next-parser.config.*",),
        config=(
            ConfigHint(
                "i18next-parser.config.*",
                r"""output\s*:\s*['"`]\.?/?([^'"`$]*?)/?\$LOCALE""",
            ),
            ConfigHint("next-i18next.config.*", rf"localePath\s*:[^'\"`\n]*{_QUOTED}"),
        ),
        trees=("public/locales", "locales", "src/locales", "src/i18n/locales", "src/i18n"),
        format=LocaleFormat.JSON,
        placeholders=(Style.DOUBLE_BRACES, Style.NESTING, Style.TAGS),
    ),
    Preset(
        name="formatjs",
        library="FormatJS, react-intl",
        example="lang/<lng>.json",
        packages=("react-intl", "@formatjs/intl", "@formatjs/cli"),
        trees=("lang", "src/lang", "locales", "src/locales", "src/i18n"),
        format=LocaleFormat.JSON,
        placeholders=(Style.ICU, Style.TAGS),
    ),
    Preset(
        name="transloco",
        library="Transloco",
        example="src/assets/i18n/<lng>.json",
        packages=("@jsverse/transloco", "@ngneat/transloco"),
        files=("transloco.config.*",),
        config=(
            ConfigHint("transloco.config.*", rf"""rootTranslationsPath['"]?\s*:\s*{_QUOTED}"""),
        ),
        trees=("src/assets/i18n", "public/i18n", "public/assets/i18n"),
        format=LocaleFormat.JSON,
        placeholders=(Style.DOUBLE_BRACES,),
    ),
    Preset(
        name="ngx-translate",
        library="ngx-translate",
        example="src/assets/i18n/<lng>.json",
        packages=("@ngx-translate/core",),
        trees=("src/assets/i18n", "public/i18n", "public/assets/i18n"),
        format=LocaleFormat.JSON,
        placeholders=(Style.DOUBLE_BRACES,),
    ),
    Preset(
        name="angular",
        library="Angular i18n",
        example="src/locale/messages.<lng>.xlf",
        packages=("@angular/localize",),
        config=(
            ConfigHint("angular.json", r'(?s)"i18n"\s*:\s*\{.*?"([^"]+\.(?:xlf|xliff|json|arb))"'),
        ),
        trees=("src/locale", "src/locales"),
        format=LocaleFormat.XLIFF,
        placeholders=(Style.ICU, Style.TAGS),
    ),
    Preset(
        name="paraglide",
        library="Paraglide (inlang)",
        example="messages/<lng>.json",
        packages=("@inlang/paraglide-js", "@inlang/paraglide-sveltekit", "@inlang/paraglide-next"),
        files=("project.inlang/settings.json",),
        config=(
            ConfigHint("project.inlang/settings.json", r'"pathPattern"\s*:\s*"\.?/?([^"{]*?)/?\{'),
        ),
        trees=("messages",),
        format=LocaleFormat.JSON,
        placeholders=(Style.ICU,),
    ),
    Preset(
        name="svelte-i18n",
        library="svelte-i18n",
        example="src/lib/i18n/locales/<lng>.json",
        packages=("svelte-i18n",),
        trees=("src/lib/i18n/locales", "src/lib/locales", "src/locales", "locales", "src/lang"),
        format=LocaleFormat.JSON,
        placeholders=(Style.ICU,),
    ),
    Preset(
        name="vue-i18n",
        library="vue-i18n",
        example="src/locales/<lng>.json",
        packages=("vue-i18n", "petite-vue-i18n", "@intlify/unplugin-vue-i18n"),
        trees=("src/locales", "locales", "src/i18n/locales", "src/lang", "lang"),
        placeholders=(Style.ICU, Style.LINKED, Style.RAILS),
    ),
    Preset(
        name="rails",
        library="Rails I18n",
        example="config/locales/<lng>.yml",
        packages=("rails", "rails-i18n"),
        trees=("config/locales",),
        format=LocaleFormat.YAML,
        placeholders=(Style.RAILS,),
    ),
    Preset(
        name="django",
        library="Django",
        example="locale/<lng>/LC_MESSAGES/django.po",
        packages=("django",),
        files=("manage.py",),
        config=tuple(
            ConfigHint(settings, r"""LOCALE_PATHS\s*=\s*[\[(][^'"\]]*?['"]\.?/?([^'"]+?)/?['"]""")
            for settings in ("*/settings.py", "*/settings/*.py", "settings.py")
        ),
        trees=("locale",),
        format=LocaleFormat.PO,
        placeholders=(Style.PRINTF,),
    ),
    Preset(
        name="flutter",
        library="Flutter gen-l10n",
        example="lib/l10n/app_<lng>.arb",
        packages=("flutter_localizations",),
        files=("l10n.yaml",),
        config=(
            ConfigHint("l10n.yaml", r"""(?m)^arb-dir\s*:\s*['"]?\.?/?([^'"\s#]+?)/?['"]?\s*$"""),
        ),
        trees=("lib/l10n",),
        format=LocaleFormat.ARB,
        placeholders=(Style.ICU,),
    ),
)
