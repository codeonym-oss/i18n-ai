# i18n-ai

`i18n-ai` generates a website's locales from the one its authors write, with LLM agents whose
every message is checked before it is written: each placeholder kept, each plural given the
target language's forms, and anything rejected sent back to the model with what is wrong.

```sh
i18n-ai scan locales/en -t fr,ar
i18n-ai generate locales/en -t fr,de,ar -m openai:gpt-4.1-mini -c "A dental clinic's booking site"
```

- **Any tree**: a directory per locale, a file per locale, or one bundle of them all, in JSON or
  YAML, its comments kept.
- **A precheck first**: the tree, which files qualify, and what each target needs, shown before
  anything is sent to a model.
- **Parallel agents**: LangGraph runs one agent per file and target locale.
- **Checked, then retried**: `{{name}}`, `{count}`, `%{name}`, `%s`, `$t(key)`, tags and ICU
  MessageFormat, validated on every message.
- **Any provider**: whatever LangChain's `init_chat_model` knows, its package installed when
  first needed.
- **Incremental**: the good translations a target already has are kept.

Start with [Getting started](guide/getting-started.md). [Locale trees](guide/trees.md) explains
the layouts it reads and writes, [The rules](guide/rules.md) what makes a translation pass, and
[Providers](guide/providers.md) how models are chosen and installed. Every option is listed under
[Commands](reference/commands.md).

```{toctree}
:hidden:
:caption: Guide

guide/getting-started
guide/trees
guide/rules
guide/providers
```

```{toctree}
:hidden:
:caption: Reference

reference/commands
```

```{toctree}
:hidden:
:caption: Design

design/architecture
design/glossary
```
