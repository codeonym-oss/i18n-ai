# Getting started

## Install

```sh
uv tool install i18n-ai          # or: pipx install i18n-ai
i18n-ai --version
```

i18n-ai needs Python 3.12 or later. A provider's LangChain package (`langchain-openai`,
`langchain-anthropic`, …) is not installed with it: i18n-ai installs the one your model needs the
first time you use it, into its own environment, after asking. See [Providers](providers.md).

## Credentials

The provider reads its key from its usual environment variable: `OPENAI_API_KEY`,
`ANTHROPIC_API_KEY`, `GOOGLE_API_KEY`, `MISTRAL_API_KEY`, `GROQ_API_KEY`… A `.env` in the
working directory is read too, without overriding the environment:

```sh
# .env
OPENAI_API_KEY=sk-...
I18N_AI_MODEL=openai:gpt-4.1-mini
```

A local model through [Ollama](https://ollama.com) needs no key: `ollama pull qwen2.5:7b`, then
`-m ollama:qwen2.5:7b`.

## The precheck

Point `scan` at the source locale, and name the targets:

```sh
i18n-ai scan locales/en -t fr,ar
```

It shows the layout it found, the source locale and the other existing ones, every source file
and whether it qualifies (a JSON object of mostly text, not configuration or data), and for each
target the files it will write and how many messages need translating. Nothing is sent to a
model.

## The generation

```sh
i18n-ai generate locales/en -t fr,ar -m openai:gpt-4.1-mini -c "An online bookshop"
```

`generate` runs the same precheck, then asks before installing the provider's package if it is
missing, and before translating. `-y` skips both questions; `--dry-run` stops after the
precheck.

Each file is written as soon as its agent finishes, in the source's JSON style. The table at the
end tells, for each file and locale, what was written, how many messages were translated or
kept, and any message that kept failing the rules (it keeps its source text, and is listed).

`-c, --context` tells the model what the website is, which sets its tone and vocabulary. It is
worth one sentence.

## Run it again

A second run translates only what is missing or broken: the existing translations that pass the
rules are kept. `--overwrite` translates everything again.
