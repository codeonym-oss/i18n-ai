# Providers

A model is named `provider:model`, as LangChain's `init_chat_model` takes it:

```sh
-m openai:gpt-4.1-mini
-m anthropic:claude-sonnet-4-5
-m google_genai:gemini-2.5-flash
-m ollama:qwen2.5:14b
-m groq:llama-3.3-70b-versatile
```

`I18N_AI_MODEL` sets the default. Without a provider prefix, LangChain infers it from the model's
name when it can (`gpt-…` is OpenAI).

## Installed on demand

Each provider is a package of its own: `langchain-openai`, `langchain-anthropic`,
`langchain-ollama`… i18n-ai reads the list from LangChain itself, so any provider it knows works.
When a generation needs a package that is missing, i18n-ai asks, then installs it into its own
environment, with `uv pip` when uv is there and `pip` otherwise. It is reused afterwards.

```sh
i18n-ai providers list               # every provider, its package, and whether it is installed
i18n-ai providers check openai:gpt-4.1-mini
i18n-ai providers install ollama
```

Installed with `uv tool install i18n-ai`, the packages go into the tool's own environment, not
your project's.

## Choosing a model

Translation quality follows the model. Small local models are fine for a first draft and for
languages they know well; for a website you ship, prefer a large model. Whichever you choose, a
translation that loses a placeholder or a plural is rejected and retried, then falls back to the
source text: a weak model gives you more fallbacks, not broken messages.

`--batch-size` (40 messages per call) and `--concurrency` (8 calls at once, across all agents)
tune the load on the provider; lower them for a rate-limited key or a local model.
