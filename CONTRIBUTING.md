# Contributing to i18n-ai

Thanks for helping! This guide covers the local setup and the conventions CI enforces.

## Setup

You need [uv](https://docs.astral.sh/uv/). Python versions are installed by uv as needed.

```sh
git clone git@github.com:codeonym-oss/i18n-ai.git && cd i18n-ai
uv sync                                  # .venv with the locked dev tools
uv run pre-commit install --install-hooks -t pre-commit -t commit-msg -t pre-push
uv run i18n-ai --help                    # the CLI, from your checkout
```

The hooks run the same checks as CI:

| Stage        | Checks                                                       |
|--------------|--------------------------------------------------------------|
| `pre-commit` | ruff lint + format, mypy (strict), import layers, file hygiene |
| `commit-msg` | the message is a [Conventional Commit](#commits)             |
| `pre-push`   | the branch name follows [`<type>/<issue>-<slug>`](#branches) |

Run the full suite with `uv run pytest`; a coverage below `fail_under` in `pyproject.toml` fails.
The tests never reach a model or install a package: `tests/support/fakes.py` holds a fake
gateway that "translates" by tagging each message with its locale, keeping its placeholders, and
can be told to break a message first or refuse a file. `FakeModel` puts it in the dishka
container in place of the provider's, with a model list that needs no network. The interactive
mode's questions are answered by `ScriptedPrompter`, which also records what was asked. Every test
runs with `MemoryKeyring` as the system keyring, so none reads or writes yours.

`examples/` holds a locale tree of each layout. Tests copy it to a temporary directory before
writing into it; run the CLI on a copy too.

CI runs the tests on Linux for Python 3.12 to 3.14, and on macOS and Windows for 3.12. To test
another Python version: `uv run --isolated --python 3.14 pytest`.

## Workflow

1. **Start from an issue.** Open one first if none exists.
2. **Branch** from `main` using the [branch convention](#branches).
3. **Commit** using [Conventional Commits](#commits).
4. **Open a PR** whose [title](#pull-requests) ends with the issue key and whose body says `Fixes #N`.
5. CI must be green. PRs are **squash-merged**, so the PR title becomes the commit on `main`.

`main` is protected: no direct pushes, no force-pushes, linear history, and these required checks:
`ci-ok`, `branch-name`, `commits`, `pr-title`.

## Conventions

The allowed types are the same everywhere:

| Type       | Use for                                          | In changelog |
|------------|--------------------------------------------------|--------------|
| `feat`     | a new feature                                    | Features     |
| `fix`      | a bug fix                                        | Bug Fixes    |
| `perf`     | a performance improvement                        | Performance  |
| `docs`     | documentation only                               | Documentation|
| `build`    | packaging, dependencies, build tooling           | Build        |
| `refactor` | code change that neither fixes nor adds          | hidden       |
| `test`     | tests only                                       | hidden       |
| `ci`       | CI and release workflows                         | hidden       |
| `chore`    | repo maintenance                                 | hidden       |
| `revert`   | reverting a previous commit                      | shown        |

### Branches

`<type>/<issue>-<slug>`: a type from the table, the GitHub issue number, and a short lowercase
hyphenated slug.

```text
feat/5-xliff-output
fix/23-rails-placeholders
docs/12-providers-guide
```

Branches opened by bots (`release-please--*`, `dependabot/*`) are exempt.

### Commits

Every commit follows [Conventional Commits 1.0](https://www.conventionalcommits.org/en/v1.0.0/):

```text
<type>(<optional scope>)<optional !>: <summary>

<optional body>

<optional footer(s)>
```

```text
feat(rules): check vue-i18n's linked messages
fix: keep a bundle's other locales in their order
feat!: write the targets under --output only

BREAKING CHANGE: the targets are no longer written beside the source when --output is set.
```

- Summary in the imperative, lowercase, no trailing period.
- `!` or a `BREAKING CHANGE:` footer marks a breaking change.
- The issue key is **not** required in commit messages; the branch and PR carry it.

### Pull requests

The title is a conventional commit summary **ending with the issue key**, and the body links the
issue:

```text
feat: check vue-i18n's linked messages (#5)
```

```text
Fixes #5
```

Keep a PR to one issue. Fill in the PR template's checklist.

## Code layout

Hexagonal, with every use case sent through the [mediary](https://github.com/codeonym-oss/mediary)
mediator. [CONTEXT.md](CONTEXT.md) is the glossary: use its words in code, docs and issues.

```text
src/i18n_ai/
  domain/        the rules, no I/O: locales, documents, placeholders, schemas, the rules
  application/   ports, and the intents (commands and queries) the mediator runs
  infra/         the adapters: filesystem, langchain, langgraph, packages, console
  runtime/       the settings, from the environment and .env
  di/            the composition root: dishka providers, the mediator, the bootstrap
  cli/           Typer: handlers, rendering, the runner
```

Each layer imports only the layers below it (cli → di → infra/runtime → application → domain);
the domain and the application never import LangChain, LangGraph, Typer, Rich or dishka; and the
CLI reaches the adapters only through `di`. `uv run lint-imports` checks this in pre-commit and CI.

### Adding a command or a query

Give it its own slice under `application/intents/<group>/{commands,queries}/<name>/`:

```text
application/intents/locale/commands/generate_locales/
  cmd.py        # GenerateLocalesCommand: what is asked
  handler.py    # its handler, marked @command_handler, depending on ports only
  receipt.py    # GenerationReceipt: what happened (a query has view.py instead)
```

`mediator.scan("i18n_ai.application.intents")` finds the handler; dishka's `MediaryProvider`
resolves the ports it asks for. Export the intent from `application/exports/<group>.py`, and give
a new port its adapter in `infra/adapters/` and its provider in `di/platform/`.

### Adding a placeholder syntax

The placeholder families live in `domain/sub_domains/locale/placeholders/tokens.py`. A new one
needs a `PlaceholderStyle`, its pattern, its line in the prompt's `_STYLES`
(`infra/adapters/langgraph/prompts.py`), and tests in `tests/domain/test_placeholders.py` that a
translation losing, adding or altering it is rejected.

## Documentation

The docs site is built with [Sphinx](https://www.sphinx-doc.org/), the
[Shibuya](https://shibuya.lepture.com/) theme and [MyST](https://myst-parser.readthedocs.io/)
Markdown from `docs/`. Preview it, rebuilt on every save, at http://127.0.0.1:8000:

```sh
uv run --group docs sphinx-autobuild -b dirhtml docs docs/_build/html
```

CI builds the site with `-W`, so broken links and references fail the build.
[Read the Docs](https://app.readthedocs.org/) builds and hosts it from `.readthedocs.yaml`:
`latest` is `main`, each release tag gets its own version, and `stable` is the newest release.
It is served at <https://docs.codeonym.work/projects/i18n-ai/>.

## Releases

Releases are automated with [release-please](https://github.com/googleapis/release-please). Merges
to `main` keep a `chore(main): release X.Y.Z` PR up to date; merging it tags the release, updates
`CHANGELOG.md` and publishes to PyPI through Trusted Publishing. Never edit the version by hand.

Versions follow [SemVer](https://semver.org/). Before 1.0.0, breaking changes bump the minor version.

## Reporting bugs and security issues

- Bugs and feature ideas: [open an issue](https://github.com/codeonym-oss/i18n-ai/issues/new/choose).
- Security vulnerabilities: see [SECURITY.md](SECURITY.md). Please don't open public issues for them.

By participating you agree to the [Code of Conduct](CODE_OF_CONDUCT.md).
