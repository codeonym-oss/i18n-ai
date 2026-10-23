from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Literal

from ...contract import ApplicationException

# Where a key was found: the environment, the project's .env, the system keyring, or typed in
# for this run only.
KeySource = Literal["env", ".env", "keyring", "run"]


@dataclass(frozen=True)
class FoundKey:
    value: str = field(repr=False)
    source: KeySource


class KeyringUnavailable(ApplicationException):
    """No usable system keyring: a headless box, a locked or missing Secret Service, ..."""

    def __init__(self, reason: str) -> None:
        super().__init__(
            message=f"no system keyring is available ({reason})",
            error_code="KEYRING_UNAVAILABLE",
            details={"reason": reason},
        )


class ICredentialStore(ABC):
    """The providers' API keys, by variable (OPENAI_API_KEY, ...). A key is looked up in the
    environment, then the project's .env, then the keys typed in for this run, then the system
    keyring: the first found wins. The store never writes a key into the environment."""

    @abstractmethod
    def find(self, variable: str) -> FoundKey | None:
        raise NotImplementedError

    @abstractmethod
    def use(self, variable: str, value: str) -> None:
        """Use `value` for the rest of this run, without saving it."""
        raise NotImplementedError

    @abstractmethod
    def save(self, variable: str, value: str) -> None:
        """Save `value` in the system keyring. Raises `KeyringUnavailable`."""
        raise NotImplementedError

    @abstractmethod
    def remove(self, variable: str) -> bool:
        """Remove the key from the system keyring; False when it was not there. Raises
        `KeyringUnavailable`."""
        raise NotImplementedError

    @abstractmethod
    def keyring(self) -> str | None:
        """The system keyring's name (macOS Keychain, SecretService Keyring, ...), or None when
        there is no usable one."""
        raise NotImplementedError
