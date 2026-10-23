from dataclasses import dataclass

from .....ports.provider import KeySource


@dataclass(frozen=True)
class KeyReceipt:
    """`saved` in the system keyring, or else used for this run, with the `problem` that kept it
    from the keyring when it was to be saved. `source` is where the provider's key now comes
    from: the environment and the .env win over the keyring."""

    provider: str
    variable: str
    saved: bool
    source: KeySource | None
    problem: str | None = None
