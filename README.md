# i18n-ai

Generate a website's locales from its source locale tree, with LLM agents that keep every
placeholder intact.

> Work in progress: the tool lands through the issues of this repository.

## Development

```sh
uv sync
uv run pytest
uv run mypy              # strict
uv run lint-imports      # the layers
uv run ruff check && uv run ruff format
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for the conventions.
