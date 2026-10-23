# Locale trees

i18n-ai reads three layouts, in any of its [formats](#formats), and writes each target in the
same layout and format as its source.

## A directory per locale

```text
locales/
├── en/
│   ├── common.json
│   └── auth/login.json
└── fr/
    └── common.json
```

Point at the source's directory (`locales/en`) or at the one holding the locales (`locales`).
Every locale file under the source is a source file, known by its path inside it (`auth/login.json`);
hidden directories and `node_modules` are skipped. `--include` and `--exclude` take globs over
these paths:

```sh
i18n-ai generate locales -s en -t de --include "auth/*" --exclude "legacy/*"
```

## A file per locale

```text
messages/
├── en.json
└── fr.json
```

Point at `messages/en.json`, or at `messages`. The names may share a prefix, as Flutter's do:
`lib/l10n/app_en.arb` gives `app_fr.arb`.

## A bundle

```json
{
  "en": { "title": "Welcome" },
  "es": { "title": "Bienvenido" }
}
```

One file whose keys are locale codes. A target is written under its own key; the other locales,
their order and the file's style are kept.

## Formats

| Format | Extensions | Used by |
|---|---|---|
| JSON | `.json` | i18next, next-intl, vue-i18n, ngx-translate, FormatJS |
| YAML | `.yml`, `.yaml` | Rails, vue-i18n, Symfony, Hugo |
| ARB | `.arb` | Flutter (`gen-l10n`, `intl`) |

The format is told by the extension. A tree keeps to one: when the source mixes them
(`en/app.json` beside `en/mail.yml`), `scan` and `generate` refuse it, and `--format` names the
one to translate, the other files being left alone.

A file whose only key is its locale holds its messages under it, as Rails writes them:

```yaml
en:
  users:
    greeting: "Welcome back, %{name}!"
```

Its targets are rooted at their own locale (`fr:` in `fr.yml`).

An ARB file's messages are ICU MessageFormat, checked as such. Its `@@` entries describe the file
and its `@key` entries describe a message for `gen-l10n`; neither is translated. A target gets the
source's `@@` entries, with `@@locale` set to its own locale, and no `@key` entry from the
source, since `gen-l10n` reads them from the template only. The ones a target already has are
kept. A new ARB locale is spelled with underscores, as Flutter's file names are: `app_pt_BR.arb`.

## The source locale

When the path names a locale (`locales/en`, `en.json`), it is the source. Otherwise it is the one
`--source` names, else `en`, else the only locale there is.

## Where the targets go

Beside the source by default: `locales/en` gives `locales/fr`, `messages/en.json` gives
`messages/fr.json`. `--output` names another directory. An existing locale keeps its spelling
(`pt_BR` stays `pt_BR` when asked for `pt-BR`).

Each target is written the way its source is: its indentation, its line endings and final
newline, and UTF-8 without escapes. Keys keep the source's order, and numbers, booleans, empty
strings and Ruby symbols (`:year`) are copied. A YAML target is the source's own document with
its messages translated, so its comments, its quoting and its block scalars (`|`, `>`) survive.

## What qualifies

A source file qualifies when it is an object whose values are mostly text. Configuration,
data and lists of codes do not, and are reported as ignored. When it qualifies, the model then
confirms it holds user-facing messages, and says what they are for (`sign-in screens`), which the
translators get as context; `--no-classify` skips that check.
