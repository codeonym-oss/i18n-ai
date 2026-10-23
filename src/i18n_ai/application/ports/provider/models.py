from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class ModelInfo:
    """A model a provider serves. `created` is a Unix time, when the provider tells it; `rank`
    places a recommended model, 0 first, and is None for the others."""

    id: str
    created: float | None = None
    rank: int | None = None


@dataclass(frozen=True)
class ModelListing:
    """A provider's models: from its API (`live`), or else the recommended ones, with the
    `problem` that kept the API from answering."""

    models: tuple[ModelInfo, ...]
    live: bool
    problem: str | None = None


class IModelLister(ABC):
    """Lists the models of a provider."""

    @abstractmethod
    async def models(self, provider: str) -> ModelListing:
        """Never raises for a missing key or network: the listing tells the problem."""
        raise NotImplementedError
