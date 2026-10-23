from dataclasses import dataclass


@dataclass(frozen=True)
class ProviderView:
    name: str
    package: str
    installed: bool
    key: str | None
    key_set: bool
