from dataclasses import dataclass

from .....ports.provider import KeySource


@dataclass(frozen=True)
class KeyRemoval:
    """`removed` is False when the keyring held no key for the provider; `source` is where its
    key still comes from, the environment or the .env, if anywhere."""

    provider: str
    variable: str
    removed: bool
    source: KeySource | None
