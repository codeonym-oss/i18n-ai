# Commands

```text
i18n-ai [-v | -vv] [--version] [COMMAND]
```

`-v` shows the steps, `-vv` everything, including the HTTP requests. `i18n-ai` alone, at a
terminal, is a guided `generate`: every option it needs is asked for. Elsewhere it shows this
help.

## `i18n-ai scan [PATH]`

The precheck alone: the tree, its source files and whether each qualifies, and what each target
needs. Nothing is sent to a model. With no `PATH`, the tree is where the project's
[preset](../guide/frameworks.md) finds its locales, else the project's only locale tree.

| Option | |
|---|---|
| `-t, --target` | A locale to plan for; repeat it, or separate with commas. |
| `-s, --source` | The source locale, when the tree has several. |
| `-o, --output` | Where the targets go. Default: beside the source. |
| `--include`, `--exclude` | Globs over the source's file names; repeat them. |
| `-f, --format` | `json`, `yaml`, `arb`, `po` or `xliff`: read only that format's files, when the tree mixes several. |
| `--preset` | The project's i18n library, in place of the one detected: where its locales are, and the format read when they mix several, the others named as left alone. |

## `i18n-ai generate [PATH]`

The precheck, then the generation. With no `PATH`, the tree is found as `scan` finds it. At a
terminal, the tree (the preset's first), a missing target, source (when the tree cannot tell
it), model or API key is asked for; see [Getting started](../guide/getting-started.md).

| Option | |
|---|---|
| `-t, --target` | A locale to generate; repeat it, or separate with commas. Asked for when missing. |
| `-m, --model` | `provider:model`. Default: `I18N_AI_MODEL`. |
| `-s, --source` | The source locale, when the tree has several (default `en`, or the only one). |
| `-o, --output` | Where the targets go. Default: beside the source. |
| `-c, --context` | What the website is, to set the tone and vocabulary. |
| `--include`, `--exclude` | Globs over the source's file names; repeat them. |
| `-f, --format` | `json`, `yaml`, `arb`, `po` or `xliff`: read only that format's files, when the tree mixes several. |
| `--preset` | The project's i18n library, in place of the one detected. |
| `--overwrite` | Translate every message again, instead of keeping the good existing ones. |
| `--strict` | Write no file that has a message which kept failing the rules. |
| `--no-classify` | Skip the model's check that each file is a locale document. |
| `--batch-size` | Messages per call to the model (40). |
| `--concurrency` | Calls to the model at once, across all agents (8). |
| `--max-attempts` | Attempts per message before it falls back to its source (3, at most 10). |
| `--temperature` | The model's temperature; the provider's default if unset. |
| `-y, --yes` | Skip the confirmations, installing the provider's package if needed. |
| `--dry-run` | Stop after the precheck. |
| `--no-input` | Ask nothing: a missing target, or a tree no preset finds, is an error. Implied on CI and when piped. |

## `i18n-ai presets`

Every preset: its library, the packages and files it is detected from, where it keeps its
locales, their format and placeholders. The one the working directory uses is marked, and said
with where its locales are. See [Your framework](../guide/frameworks.md).

## `i18n-ai providers`

| Command | |
|---|---|
| `providers list` | Every provider LangChain knows, its package, whether it is installed, and its API key's variable and where that key comes from. |
| `providers models PROVIDER` | The provider's models, from its API, the recommended first, then the newest. Exit 2, with the reason, when the list cannot be read (no key, no network). |
| `providers check MODEL` | A model's provider and package, and whether it is installed (exit 1 if not). |
| `providers install PROVIDER` | Install a provider's package, unless it is there. |

## `i18n-ai auth`

| Command | |
|---|---|
| `auth login [PROVIDER]` | Save the provider's API key in the system keyring. The key is asked for, hidden, or read from stdin when piped. Exit 2 when there is no keyring, the provider takes no key, or no key was given. |
| `auth logout [PROVIDER]` | Remove the provider's key from the system keyring; `--all` removes every provider's. |
| `auth status` | The system keyring, and for each provider where its key comes from: the environment, the `.env`, or the keyring. Never the keys. |

At a terminal, a missing provider is asked for. A key is looked up in the environment, then the
`.env`, then the keyring, and the first found wins.

## Exit codes

| Code | |
|---|---|
| 0 | Done. |
| 1 | Something was not written: a file failed or was refused (`--strict`), nothing qualified, or you declined. |
| 2 | A refusal, with one `error:` line: no tree, an unknown source, preset or provider, a target that is the source, invalid settings. |
| 130 | Interrupted. |

## Environment

| Variable | |
|---|---|
| `I18N_AI_MODEL` | The default `--model`. |
| `I18N_AI_BATCH_SIZE`, `I18N_AI_CONCURRENCY`, `I18N_AI_MAX_ATTEMPTS` | The defaults of those options. |
| `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `OLLAMA_HOST`, … | The provider's own settings. A key set here wins over the one in the keyring. |
| `PYTHON_KEYRING_BACKEND` | `keyring`'s own: the keyring to use, e.g. `keyring.backends.fail.Keyring` for none. |
| `I18N_AI_STATE_DIR` | Where the interactive mode remembers its answers. Default: `~/.local/state/i18n-ai`, `~/Library/Application Support/i18n-ai` or `%LOCALAPPDATA%\i18n-ai`. |
| `CI` | When true, nothing is asked, as with `--no-input`. |

A `.env` in the working directory is read first, without overriding the environment.
