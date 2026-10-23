from abc import ABC, abstractmethod
from dataclasses import dataclass

from ....domain.exports.provider import ModelSpec, ResolvedModel
from .credentials import KeySource


@dataclass(frozen=True)
class ProviderInfo:
    """A provider LangChain integrates, whether its package is installed, and the environment
    variable holding its API key (None when it takes no key, or several settings), and where
    that key was found, if it was."""

    name: str
    package: str
    module: str
    installed: bool
    key: str | None = None
    key_source: KeySource | None = None

    @property
    def key_set(self) -> bool:
        return self.key_source is not None


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
