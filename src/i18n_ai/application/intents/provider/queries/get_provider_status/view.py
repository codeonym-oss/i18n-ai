from dataclasses import dataclass


@dataclass(frozen=True)
class ProviderStatusView:
    provider: str
    model: str
    package: str
    installed: bool
