# Commands

```text
i18n-ai [-v | -vv] [--version] COMMAND
```

`-v` shows the steps, `-vv` everything, including the HTTP requests.

## `i18n-ai scan PATH`

The precheck alone: the tree, its source files and whether each qualifies, and what each target
needs. Nothing is sent to a model.

| Option | |
|---|---|
| `-t, --target` | A locale to plan for; repeat it, or separate with commas. |
| `-s, --source` | The source locale, when the tree has several. |
| `-o, --output` | Where the targets go. Default: beside the source. |
| `--include`, `--exclude` | Globs over the source's file names; repeat them. |

## `i18n-ai generate PATH`

The precheck, then the generation.

| Option | |
|---|---|
| `-t, --target` | A locale to generate; repeat it, or separate with commas. Required. |
| `-m, --model` | `provider:model`. Default: `I18N_AI_MODEL`. |
| `-s, --source` | The source locale, when the tree has several (default `en`, or the only one). |
| `-o, --output` | Where the targets go. Default: beside the source. |
| `-c, --context` | What the website is, to set the tone and vocabulary. |
| `--include`, `--exclude` | Globs over the source's file names; repeat them. |
| `--overwrite` | Translate every message again, instead of keeping the good existing ones. |
| `--strict` | Write no file that has a message which kept failing the rules. |
| `--no-classify` | Skip the model's check that each file is a locale document. |
| `--batch-size` | Messages per call to the model (40). |
| `--concurrency` | Calls to the model at once, across all agents (8). |
| `--max-attempts` | Attempts per message before it falls back to its source (3, at most 10). |
| `--temperature` | The model's temperature; the provider's default if unset. |
| `-y, --yes` | Skip the confirmations, installing the provider's package if needed. |
| `--dry-run` | Stop after the precheck. |

## `i18n-ai providers`

| Command | |
|---|---|
| `providers list` | Every provider LangChain knows, its package, and whether it is installed. |
| `providers check MODEL` | A model's provider and package, and whether it is installed (exit 1 if not). |
| `providers install PROVIDER` | Install a provider's package, unless it is there. |

## Exit codes

| Code | |
|---|---|
| 0 | Done. |
| 1 | Something was not written: a file failed or was refused (`--strict`), nothing qualified, or you declined. |
| 2 | A refusal, with one `error:` line: no tree, an unknown source or provider, a target that is the source, invalid settings. |
| 130 | Interrupted. |

## Environment

| Variable | |
|---|---|
| `I18N_AI_MODEL` | The default `--model`. |
| `I18N_AI_BATCH_SIZE`, `I18N_AI_CONCURRENCY`, `I18N_AI_MAX_ATTEMPTS` | The defaults of those options. |
| `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `OLLAMA_HOST`, … | The provider's own settings. |

A `.env` in the working directory is read first, without overriding the environment.
