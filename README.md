# i18n-ai

[![ci](https://github.com/codeonym-oss/i18n-ai/actions/workflows/ci.yml/badge.svg)](https://github.com/codeonym-oss/i18n-ai/actions/workflows/ci.yml)
[![docs](https://img.shields.io/badge/docs-docs.codeonym.work-teal)](https://docs.codeonym.work/projects/i18n-ai/)
[![license](https://img.shields.io/badge/license-MIT-blue)](LICENSE)

Generate a website's locales from its source locale tree, with LLM agents that keep every
placeholder intact.

```sh
i18n-ai generate locales/en -t fr,de,ar -m openai:gpt-4.1-mini -c "A dental clinic's booking site"
```

- **Any tree.** A directory per locale (`locales/en/**/*.json`), a file per locale
  (`messages/en.json`), or one bundle holding them all (`{"en": {...}, "fr": {...}}`). The
  targets are written beside the source, in its JSON style (indent, final newline, UTF-8).
- **A precheck first.** The tree, its source files and whether each qualifies, and what each target
  needs, shown before anything is sent to a model, for you to confirm.
- **Parallel agents.** LangGraph classifies every file in parallel, then runs one agent per
  file and locale, each translating its messages in batches.
- **Checked, then retried.** Every translation is checked against the rules below, and a rejected
  one goes back to the model with what is wrong, until it passes or runs out of attempts.
- **Any provider.** Whatever LangChain's `init_chat_model` knows: OpenAI, Anthropic, Google,
  Mistral, Groq, Ollama, Bedrock, OpenRouter… A provider's package is installed when first needed,
  and reused afterwards.
- **Incremental.** The existing translations of a target that pass the rules are kept; only the
  missing and broken ones are translated (`--overwrite` redoes them all).

## Install

```sh
uv tool install i18n-ai          # or: pipx install i18n-ai
```

The provider's credentials come from its usual environment variables (`OPENAI_API_KEY`,
`ANTHROPIC_API_KEY`, `GOOGLE_API_KEY`, `OLLAMA_HOST`, …), which a `.env` in the working directory
can hold.

## Usage

```sh
i18n-ai scan locales/en -t fr,ar                 # the precheck alone
i18n-ai generate locales/en -t fr -t pt-BR -m anthropic:claude-sonnet-4-5
i18n-ai generate messages/en.json -t ja -m ollama:qwen2.5:14b --dry-run
i18n-ai generate locales -s en -t de --include "auth/*" --exclude "legacy/*" -y
i18n-ai providers list | install ollama | check openai:gpt-4.1-mini
```

| Option | |
|---|---|
| `-t, --target` | A locale to generate; repeat it, or separate with commas. |
| `-m, --model` | `provider:model`. Default: `I18N_AI_MODEL`. |
| `-s, --source` | The source locale, when the tree has several (default `en`, or the only one). |
| `-o, --output` | Where the targets go. Default: beside the source. |
| `-c, --context` | What the website is, to set the tone and vocabulary. |
| `--include`, `--exclude` | Globs over the source's file names. |
| `--overwrite` | Translate every message again, instead of keeping the good existing ones. |
| `--strict` | Write no file that has a message which kept failing the rules. |
| `--no-classify` | Skip the model's check that each file is a locale document. |
| `--batch-size`, `--concurrency`, `--max-attempts` | Messages per call (40), calls at once (8), attempts per message (3). Also `I18N_AI_BATCH_SIZE`, … |
| `-y, --yes`, `--dry-run` | Skip the confirmations (installing the provider if needed); or stop after the precheck. |

Exit codes: 0 done, 1 something was not written (or nothing qualified, or you declined), 2 a refusal
(no tree, unknown provider, …).

## How it works

```
              ┌────────────── run graph ───────────────┐
 precheck ──▶ │ classify ×files ─▶ plan ─▶ atom ×(files × locales) │ ──▶ write each file as it lands
              └────────────────────────────────────────┘

 atom:  extract_schema ─▶ translate ─▶ validate ─▶ assemble
                             ▲            │
                             └── retry ◀──┘   rejected messages, with their problems
```

1. **Precheck** (`scan`): finds the layout and the source, reads every source file, and *qualifies*
   it: a JSON object whose values are mostly text. Config and data files are ignored.
2. **Classify**: the model confirms each qualifying file holds user-facing messages, and says what
   they are for ("sign-in screens"), which the translators get as context.
3. **Extract the schema**: the target's shape. Keys and order are the source's, and numbers,
   booleans and empty strings are copied. A slot is made for each message, with the
   placeholders it must keep. i18next plural families take the **target's** CLDR categories:
   `item_one`/`item_other` becomes six keys in Arabic and one in Japanese.
4. **Translate** in batches, at most `--concurrency` calls at once across all agents.
5. **Validate** each answer, and send the rejected ones back with their problems.
6. **Assemble** the document. A message that never passed keeps its source text, and is reported
   (or, with `--strict`, the file is not written).

### The rules

A translation is **rejected** when it:

- is empty or missing;
- loses, adds or alters a placeholder, counted as often as it appears: `{{name}}`, `{{count, number}}`,
  `{name}`, `{n, number}`, `%{name}`, `%s`, `%1$d`, `%(name)s`, `$t(key)`, `@:key`, and tags such as
  `<b>`, `</b>`, `<0/>`;
- breaks ICU MessageFormat, drops a plural's explicit selector (`=0`), changes a select's options,
  or changes the placeholders inside a plural's or select's branches;
- hides an argument behind an ICU apostrophe (`l'{count}`); the model is told to write `’` instead.

It is **kept, with a warning**, when an ICU plural lacks some of the target's categories, or a
message is left as in the source. An i18next plural form may show the count or not (Russian's
`one` is also 21, English's is not). Leading and trailing whitespace is copied from the source.

## Architecture

Hexagonal, CQRS over [mediary](https://github.com/codeonym-oss/mediary), wired with dishka:

```
src/i18n_ai/
├── domain/            the rules, no I/O
│   ├── contract/      base exceptions
│   ├── sub_domains/
│   │   ├── locale/    LocaleCode, KeyPath, layouts · LocaleDocument, LocaleTree
│   │   │              placeholders/ (tokens, ICU parser, signatures) · schema/ · rules/
│   │   └── provider/  ModelSpec, ResolvedModel
│   └── exports/       each sub-domain's public names
├── application/
│   ├── ports/         locale (scanner, store, engine) · provider (catalog, installer) · progress
│   ├── intents/       locale: ScanLocaleTreeQuery, GenerateLocalesCommand
│   │                  provider: ListProvidersQuery, GetProviderStatusQuery, InstallProviderCommand
│   └── exports/
├── infra/adapters/    filesystem · langchain (catalog, chat models) · langgraph (run graph, atom,
│                      gateway, prompts) · packages (uv / pip) · console (progress)
├── di/                platform providers · messaging (mediator, scanned) · container · bootstrap
├── runtime/           settings, from the environment and .env
└── cli/               Typer: handlers, rendering, the runner
```

Each intent is a slice, `cmd.py`/`query.py`, `handler.py`, and `receipt.py`/`view.py`. Its handler is
marked `@command_handler`/`@query_handler`, and `mediator.scan` finds it. dishka's `MediaryProvider`
resolves the handlers' ports for each request.

## Development

```sh
uv sync
uv run pytest            # domain rules, the scanner, the CLI, and whole runs against a fake model
uv run mypy              # strict
uv run lint-imports      # the layers
uv run ruff check && uv run ruff format
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for the conventions, and the
[docs](https://docs.codeonym.work/projects/i18n-ai/) for the guide.
