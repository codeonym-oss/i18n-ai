# Locale trees

i18n-ai reads three layouts, and writes each target in the same one.

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
Every `.json` under the source is a source file, known by its path inside it (`auth/login.json`);
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

Point at `messages/en.json`, or at `messages`.

## A bundle

```json
{
  "en": { "title": "Welcome" },
  "es": { "title": "Bienvenido" }
}
```

One file whose keys are locale codes. A target is written under its own key; the other locales,
their order and the file's style are kept.

## The source locale

When the path names a locale (`locales/en`, `en.json`), it is the source. Otherwise it is the one
`--source` names, else `en`, else the only locale there is.

## Where the targets go

Beside the source by default: `locales/en` gives `locales/fr`, `messages/en.json` gives
`messages/fr.json`. `--output` names another directory. An existing locale keeps its spelling
(`pt_BR` stays `pt_BR` when asked for `pt-BR`).

Each target is written in the source's JSON style: its indentation, its final newline, and UTF-8
without escapes. Keys keep the source's order, and numbers, booleans and empty strings are
copied.

## What qualifies

A source file qualifies when it is a JSON object whose values are mostly text. Configuration,
data and lists of codes do not, and are reported as ignored. When it qualifies, the model then
confirms it holds user-facing messages, and says what they are for (`sign-in screens`), which the
translators get as context; `--no-classify` skips that check.
