from dataclasses import dataclass


@dataclass(frozen=True)
class LocaleView:
    code: str
    name: str
    direction: str
