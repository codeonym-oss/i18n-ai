# Architecture

## The run

```text
              ┌──────────────────────── run graph ────────────────────────┐
 precheck ──▶ │ classify ×files ─▶ plan ─▶ atom ×(files × locales)        │ ──▶ write each file as it lands
              └───────────────────────────────────────────────────────────┘

 atom:  extract_schema ─▶ translate ─▶ validate ─▶ assemble
                             ▲            │
                             └── retry ◀──┘   rejected messages, with their problems
```

1. **Precheck**: the scanner finds the layout and the source, reads every source file, and the
   rules qualify each one. The plan counts, for each target, the messages to translate and the
   existing ones to keep.
2. **Classify**: one LangGraph `Send` per qualifying file asks the model to confirm it, and what
   it is for. A model that cannot be reached is not fatal here: the rules already qualified the
   file, and its translation will report the failure.
3. **Atoms**: one `Send` per file and target runs the atom subgraph. It extracts the target's
   [schema](glossary.md), translates its units in batches, validates each answer, sends the
   rejected ones back with their problems, and assembles the document.
4. **Writes**: the engine streams each atom's outcome as it finishes, and the command's handler
   writes that file at once, atomically.

Every call to the model shares one semaphore, so `--concurrency` holds across all agents.

## The layers

Hexagonal, with CQRS over [mediary](https://github.com/codeonym-oss/mediary) and dependency
injection by [dishka](https://dishka.readthedocs.io/):

```text
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

Each intent is a slice: `cmd.py` or `query.py`, `handler.py`, and `receipt.py` or `view.py`. Its
handler is marked `@command_handler` or `@query_handler`, and `mediator.scan` finds it. dishka's
`MediaryProvider` resolves the ports each handler asks for, in a request scope the CLI opens per
command.

`lint-imports` holds the layers in place: each imports only those below it, the domain and the
application import no I/O library, and the CLI reaches the adapters only through `di`.

## Why

- **The rules are the domain.** What makes a translation right (its placeholders, its plurals) is
  pure Python on strings, tested without a model, and the same whether the model is GPT or a 3B
  local one.
- **The model is an adapter.** The application asks an `ITranslationEngine` for events; LangGraph
  and LangChain live behind it, and tests replace the gateway with a fake.
- **Providers are data.** The list comes from LangChain's own table, so a provider it adds works
  without a release of i18n-ai.
