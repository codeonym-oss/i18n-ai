from dataclasses import dataclass


@dataclass(frozen=True)
class ModelView:
    id: str
    recommended: bool
    created: float | None


@dataclass(frozen=True)
class ModelsView:
    """A provider's models, the recommended first, then the newest. `live` when they come from
    the provider's API; otherwise they are the recommended ones, and `problem` says why."""

    provider: str
    models: tuple[ModelView, ...]
    live: bool
    problem: str | None
