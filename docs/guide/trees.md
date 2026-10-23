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
`lib/l10n/app_en.arb` gives `app_fr.arb`, and Symfony's: `translations/messages.en.xlf` gives
`messages.fr.xlf`.

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
| gettext PO | `.po`, `.pot` | Django, WordPress, Babel, GNU projects |
| XLIFF 1.2, 2.0 | `.xlf`, `.xliff` | Angular, Symfony, translation tools |

The format is told by the extension. A tree keeps to one: when the source mixes them
(`en/app.json` beside `en/mail.yml`), `scan` and `generate` refuse it, and `--format` names the
one to translate, the other files being left alone.

### YAML

A file whose only key is its locale holds its messages under it, as Rails writes them:

```yaml
en:
  users:
    greeting: "Welcome back, %{name}!"
```

Its targets are rooted at their own locale (`fr:` in `fr.yml`).

### ARB

An ARB file's messages are ICU MessageFormat, checked as such. Its `@@` entries describe the file
and its `@key` entries describe a message for `gen-l10n`; neither is translated. A message's
`description` is given to the model beside it, so that a short label (`Save`, `Post`) is
translated in the sense its author meant. A target gets the
source's `@@` entries, with `@@locale` set to its own locale, and no `@key` entry from the
source, since `gen-l10n` reads them from the template only. The ones a target already has are
kept. A new ARB locale is spelled with underscores, as Flutter's file names are: `app_pt_BR.arb`.

### gettext

A catalog's messages are its entries, each keyed by its `msgid` (and its `msgctxt`). The source
text is the `msgid`, so a gettext tree needs no source locale. Its template is:

- its `.pot` (`po/notes.pot` beside `fr.po`, or Babel's `locale/messages.pot` beside
  `fr/LC_MESSAGES/messages.po`); point at the `.pot`, or at its directory;
- else, in a directory per locale, each catalog's latest version among the locales: Django's
  `locale/fr/LC_MESSAGES/django.po` is the template of `locale/ar/LC_MESSAGES/django.po`.

A target is the template with its `msgstr` filled. Its comments, references (`#:`), flags and
order are kept, and its header gets its `Language`, `Language-Team` and `Last-Translator`
(`i18n-ai`). An existing catalog keeps its header and its translations, and gets the template's
new entries; a fuzzy entry is translated again. Catalogs are named as their siblings are
(`plugin-fr_FR.po` beside `plugin.pot`), a new locale with underscores (`pt_BR`).

A plural entry gets the target's forms. An existing catalog keeps its own `Plural-Forms`: which
CLDR category each `msgstr[n]` is for is read from it, so an old Russian catalog keeps its three
forms. A new catalog gets CLDR's rule, written as gettext's `Plural-Forms`.

The extracted comments (`#.`) and the context (`msgctxt`) are given to the model as the
message's note.

### XLIFF

An XLIFF file holds each message's source text and its translation: a unit's `<source>` and
`<target>` in XLIFF 1.2 (`<trans-unit>`), each of its segments' in XLIFF 2.0 (`<unit>`,
`<segment>`). A message is keyed by its unit's `id`. A file with no locale in its name is a
template, as Angular's `ng extract-i18n` writes it: point at `src/locale/messages.xlf`, or at its
directory, and its targets are `messages.fr.xlf`. In a source locale's own file, as Symfony
writes `translations/messages.en.xlf`, a message's text is its `<target>`.

The elements inside a message, a placeholder (`<x id="INTERPOLATION"/>`, `<ph/>`) or a run of
bold (`<g>`, `<pc>`), are given to the model as numbered tags, `<x1/>` and `<g2>…</g2>`, which
its translation must keep, as it must any tag. A translation may move them; each is written
back as its source has it, attributes and all. Its `<note>`s, what each tag stands for (its
`equiv-text` or `disp`), and its Symfony key (`resname`) are the message's note.

A target is the template with its `<target>`s filled, its `target-language` (`trgLang` in 2.0)
its locale. Each translation is marked as a machine's, for translation tools to put it up for
review: `state="needs-review-translation" state-qualifier="mt-suggestion"` in XLIFF 1.2, and
`state="translated" subState="i18n-ai:mt"` in 2.0, whose states have no such one. Angular and
Symfony read a target whatever its state, and i18n-ai keeps it on the next run. An existing one keeps its own translations,
units and notes, and gets the template's new units and current `<source>`s; a target still
`new`, `needs-translation` or `initial` is translated again.

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
