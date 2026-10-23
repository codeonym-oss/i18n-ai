# Your framework

In a project, i18n-ai finds the i18n library from the project's manifests and config files. A
library's preset says where it keeps its locales and in which format. So `scan` and `generate`
need no path:

```console
$ i18n-ai scan -t fr
Preset flutter · flutter_localizations in pubspec.yaml → lib/l10n (from l10n.yaml)
```

`i18n-ai presets` lists the presets, and marks the one found in the working directory.

## How a preset is found

These manifests are read at the project's root:

- `package.json`
- `Gemfile`
- `pubspec.yaml`
- `composer.json`
- `pyproject.toml`, `Pipfile` and `requirements*.txt`

A library is found when one of its packages is a dependency in one of them, or when one of its
own files is there, such as `l10n.yaml` or `manage.py`.

A project may use several libraries; a Nuxt app depends on vue-i18n too. The presets are tried
in the order below, and the first one whose locales exist wins.

## Where its locales are

A preset first checks the config file that names the locale directory, if the library has one
(`angular.json`, `l10n.yaml`, …). That file is read as text, never run. If the file names no
existing directory, the preset tries the library's usual places.

If no preset is found, or its locales are in none of those places, i18n-ai looks for locale trees
in the project:

- If it finds exactly one, it uses that tree.
- If it finds none or several:
  - `scan` and `generate --no-input` stop and ask for the tree's path.
  - The interactive mode lists them for you to pick.

## Choosing a preset

`--preset` names the preset, in place of the one found:

```sh
i18n-ai scan --preset vue-i18n
i18n-ai generate locales -t de --preset rails
```

When a path is also given, the path is the tree.

A preset's format matters only when its tree mixes formats, as `config/locales` holding
`en.yml` beside `en.json`. Without a preset, `scan` and `generate` refuse such a tree until
`--format` names one. With a preset, its own format is read, and the scan's `Format` line names
the formats left alone:

```text
Format    yaml (the preset's; the json files are left alone, --format chooses)
```

A tree in one format is read in it, whatever the preset's.

At a terminal, the interactive mode lists the preset's locale directory first, as the default
answer. You can pick another tree, which is then read in its own format.

## Placeholders

Each preset lists the placeholders its library uses. For every library but Laravel they are
documentation only: every message is checked for every family i18n-ai knows, whatever the
preset. So a preset never loosens a check. See [The rules](rules.md).

Laravel's `:name` placeholders and pipe plurals are the exception. A colon or a pipe is ordinary
text in other libraries' messages, so they are checked only in Laravel's own locales: with no
path, a path in `lang/`, or `--preset laravel`.

## Laravel

| | |
|---|---|
| Found by | `laravel/framework` in `composer.json` |
| Locales | `lang`; else `resources/lang` (before Laravel 9) |
| Format | JSON, `lang/<lng>.json` |
| Placeholders | `:name`, `:Name`, `:NAME` |

A key is its English text: `lang/fr.json` holds `{"Welcome, :name!": "Bienvenue, :name !"}`.
The source is `lang/en.json` when there is one. Otherwise it is the keys of every locale file,
each key's text the key itself:

```text
Source    en English (the keys of de.json, fr.json)
```

`--source` names another language: its file when there is one, else the keys, taken as that
language. A key found only in the PHP code (`__('...')`) is not translated until a locale file
has it.

A placeholder keeps its name, as often as it appears; its case may change, `:name` becoming
`:Name` at the start of a sentence. A pipe plural, as `trans_choice` reads it, gets the target's
number of forms by Laravel's own table, which is not CLDR's: 2 in French, 3 in Russian, 1 in
Japanese. Its forms with a range (`{0} none|[1,*] some`) keep their ranges. A pipe with a
space on each side and no range is text, as in `Dashboard | Acme`.

Laravel's PHP locales, `lang/<lng>/*.php`, and `lang/vendor/` are left alone. The Laravel
preset comes first: in an Inertia app that also uses vue-i18n or i18next, name the frontend's
locales' path to translate them, with their own rules.

## Nuxt i18n

| | |
|---|---|
| Found by | `@nuxtjs/i18n` |
| Locales | `langDir` in `nuxt.config.*`, under `i18n/` and then the root; else `i18n/locales`, `locales`, `lang` |
| Format | JSON or YAML, whichever the tree holds |
| Placeholders | ICU `{name}`, links `@:key`, legacy `%{name}` |

## next-intl

| | |
|---|---|
| Found by | `next-intl` |
| Locales | `messages`, `src/messages`, `locales` |
| Format | JSON |
| Placeholders | ICU, rich-text tags `<b>…</b>` |

## i18next

For i18next, react-i18next and next-i18next.

| | |
|---|---|
| Found by | `i18next`, `react-i18next`, `next-i18next`, or an `i18next-parser.config.*` |
| Locales | the `output` of `i18next-parser.config.*`, or the `localePath` of `next-i18next.config.*`; else `public/locales`, `locales`, `src/locales`, `src/i18n/locales`, `src/i18n` |
| Format | JSON, a directory per locale and a file per namespace |
| Placeholders | `{{name}}`, nesting `$t(key)`, `<Trans>` tags |

## FormatJS

For react-intl and FormatJS.

| | |
|---|---|
| Found by | `react-intl`, `@formatjs/intl`, `@formatjs/cli` |
| Locales | `lang`, `src/lang`, `locales`, `src/locales`, `src/i18n` |
| Format | JSON |
| Placeholders | ICU, rich-text tags |

## Transloco

| | |
|---|---|
| Found by | `@jsverse/transloco`, `@ngneat/transloco`, or a `transloco.config.*` |
| Locales | `rootTranslationsPath` in `transloco.config.*`; else `src/assets/i18n`, `public/i18n`, `public/assets/i18n` |
| Format | JSON |
| Placeholders | `{{name}}` |

## ngx-translate

| | |
|---|---|
| Found by | `@ngx-translate/core` |
| Locales | `src/assets/i18n`, `public/i18n`, `public/assets/i18n` |
| Format | JSON |
| Placeholders | `{{name}}` |

## Angular i18n

| | |
|---|---|
| Found by | `@angular/localize` |
| Locales | the directory of the translation files in the `i18n` block of `angular.json`; else `src/locale`, `src/locales` |
| Format | XLIFF, from the `messages.xlf` that `ng extract-i18n` writes |
| Placeholders | ICU, and the interpolations and elements as XLIFF tags |

## Paraglide

| | |
|---|---|
| Found by | `@inlang/paraglide-js` (or its SvelteKit and Next adapters), or `project.inlang/settings.json` |
| Locales | the `pathPattern` in `project.inlang/settings.json`; else `messages` |
| Format | JSON |
| Placeholders | `{name}` |

## svelte-i18n

| | |
|---|---|
| Found by | `svelte-i18n` |
| Locales | `src/lib/i18n/locales`, `src/lib/locales`, `src/locales`, `locales`, `src/lang` |
| Format | JSON |
| Placeholders | ICU |

## vue-i18n

| | |
|---|---|
| Found by | `vue-i18n`, `petite-vue-i18n`, `@intlify/unplugin-vue-i18n` |
| Locales | `src/locales`, `locales`, `src/i18n/locales`, `src/lang`, `lang` |
| Format | JSON or YAML, whichever the tree holds |
| Placeholders | ICU `{name}`, links `@:key`, legacy `%{name}` |

## Rails

| | |
|---|---|
| Found by | `rails` or `rails-i18n` in the `Gemfile` |
| Locales | `config/locales` |
| Format | YAML, each file rooted at its locale (`en:`) |
| Placeholders | `%{name}` |

## Django

| | |
|---|---|
| Found by | `django` in `pyproject.toml`, `Pipfile` or `requirements*.txt`, or a `manage.py` |
| Locales | the first path in `LOCALE_PATHS` in `*/settings.py` or `*/settings/*.py`; else `locale` |
| Format | gettext PO, `locale/<lng>/LC_MESSAGES/django.po` |
| Placeholders | printf `%s`, `%(name)s` |

The `.po` files are not compiled: run `django-admin compilemessages` after a generation.

## Flutter

| | |
|---|---|
| Found by | `flutter_localizations` in `pubspec.yaml`, or an `l10n.yaml` |
| Locales | `arb-dir` in `l10n.yaml`; else `lib/l10n` |
| Format | ARB |
| Placeholders | ICU |

Run `flutter gen-l10n` after a generation, unless `flutter: generate: true` runs it at build time.
