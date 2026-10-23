"""The providers' API keys, looked up in the environment, the project's .env, then the system
keyring through `keyring` (macOS Keychain, Windows Credential Manager, Secret Service on Linux),
each saved as service "i18n-ai", user the key's variable. Without a usable keyring, nothing is
written anywhere else: the environment and the .env are left to the user."""

import logging
import os
from pathlib import Path

import keyring
from dotenv import dotenv_values
from keyring.backend import KeyringBackend
from keyring.errors import KeyringError, PasswordDeleteError

from ....application.ports.provider import (
    FoundKey,
    ICredentialStore,
    KeyringUnavailable,
)

logger = logging.getLogger(__name__)

SERVICE = "i18n-ai"


class KeyringCredentialStore(ICredentialStore):
    """`backend` replaces the system keyring, and `dotenv` the working directory's .env, in
    tests. The keyring's answers are kept for the run: a locked keyring asks once."""

    def __init__(self, dotenv: Path | None = None, backend: KeyringBackend | None = None) -> None:
        self._dotenv = dotenv or Path.cwd() / ".env"
        self._backend = backend
        self._dotenv_values: dict[str, str | None] | None = None
        self._saved: dict[str, str | None] = {}
        self._run: dict[str, str] = {}

    def find(self, variable: str) -> FoundKey | None:
        if value := os.environ.get(variable):
            # the settings load the .env into the environment, without overriding it
            return FoundKey(value, ".env" if self._from_dotenv(variable) == value else "env")
        if value := self._run.get(variable):
            return FoundKey(value, "run")
        if value := self._from_keyring(variable):
            return FoundKey(value, "keyring")
        return None

    def use(self, variable: str, value: str) -> None:
        self._run[variable] = value

    def save(self, variable: str, value: str) -> None:
        backend = self._usable()
        try:
            backend.set_password(SERVICE, variable, value)
        except KeyringError as error:
            raise KeyringUnavailable(_reason(error)) from error
        self._saved[variable] = value

    def remove(self, variable: str) -> bool:
        backend = self._usable()
        self._saved[variable] = None
        try:
            backend.delete_password(SERVICE, variable)
        except PasswordDeleteError:
            return False
        except KeyringError as error:
            raise KeyringUnavailable(_reason(error)) from error
        return True

    def keyring(self) -> str | None:
        try:
            return self._usable().name
        except KeyringUnavailable:
            return None

    def _usable(self) -> KeyringBackend:
        backend = self._backend or keyring.get_keyring()
        # keyring's fail and null backends, and an empty chain, rank at 0 or below
        if backend.priority <= 0:
            raise KeyringUnavailable(f"keyring found no backend, only {backend.name}")
        return backend

    def _from_keyring(self, variable: str) -> str | None:
        if variable not in self._saved:
            try:
                self._saved[variable] = self._usable().get_password(SERVICE, variable)
            except (KeyringUnavailable, KeyringError):
                logger.debug("Cannot read %s from the keyring", variable, exc_info=True)
                self._saved[variable] = None
        return self._saved[variable]

    def _from_dotenv(self, variable: str) -> str | None:
        if self._dotenv_values is None:
            self._dotenv_values = dotenv_values(self._dotenv) if self._dotenv.is_file() else {}
        return self._dotenv_values.get(variable)


def _reason(error: KeyringError) -> str:
    return str(error) or type(error).__name__
