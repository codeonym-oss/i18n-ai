from dataclasses import dataclass

from .....ports.provider import KeySource


@dataclass(frozen=True)
class KeyView:
    provider: str
    variable: str
    source: KeySource | None


@dataclass(frozen=True)
class KeysView:
    """`keyring` is the system keyring's name, or None when there is no usable one."""

    keyring: str | None
    keys: tuple[KeyView, ...]
