from abc import ABC, abstractmethod
from dataclasses import dataclass

from ....domain.exports.provider import ModelSpec, ResolvedModel


@dataclass(frozen=True)
class ProviderInfo:
    """A provider LangChain integrates, and whether its package is installed."""

    name: str
    package: str
    module: str
    installed: bool


class IProviderCatalog(ABC):
    """The providers LangChain's `init_chat_model` knows."""

    @abstractmethod
    def providers(self) -> list[ProviderInfo]:
        raise NotImplementedError

    @abstractmethod
    def provider(self, name: str) -> ProviderInfo:
        """Raises `ProviderUnknown`."""
        raise NotImplementedError

    @abstractmethod
    def resolve(self, spec: ModelSpec) -> ResolvedModel:
        """The provider and model `spec` names. Raises `ProviderUnknown`."""
        raise NotImplementedError

    @abstractmethod
    def is_installed(self, module: str) -> bool:
        raise NotImplementedError
