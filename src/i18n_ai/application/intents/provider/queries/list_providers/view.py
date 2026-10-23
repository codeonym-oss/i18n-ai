from dataclasses import dataclass

from .....ports.provider import KeySource


@dataclass(frozen=True)
class ProviderView:
    name: str
    package: str
    installed: bool
    key: str | None
    key_source: KeySource | None

    @property
    def key_set(self) -> bool:
        return self.key_source is not None
