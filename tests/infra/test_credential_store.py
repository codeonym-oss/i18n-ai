"""The providers' keys: the environment, then the .env, then a key typed in for the run, then the
keyring, which is in memory here; and a chat model that sees a keyring key only while built."""

import os
from pathlib import Path
from typing import Any

import keyring
import pytest
from keyring.backends import fail
from keyring.errors import KeyringLocked

from i18n_ai.application.ports.provider import KeyringUnavailable
from i18n_ai.domain.exports.provider import ResolvedModel
from i18n_ai.infra.adapters.keyring import SERVICE, KeyringCredentialStore
from i18n_ai.infra.adapters.langchain import LangChainChatModels
from i18n_ai.infra.adapters.langchain import chat_models as module
from support.fakes import MemoryKeyring

KEY = "OPENAI_API_KEY"


@pytest.fixture(autouse=True)
def no_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(KEY, "")
    monkeypatch.delenv(KEY)


@pytest.fixture
def store(tmp_path: Path) -> KeyringCredentialStore:
    return KeyringCredentialStore(dotenv=tmp_path / ".env")


def test_the_keyring_holds_what_is_saved(
    store: KeyringCredentialStore, vault: MemoryKeyring
) -> None:
    assert store.find(KEY) is None

    store.save(KEY, "sk-saved")

    assert vault.passwords == {(SERVICE, KEY): "sk-saved"}
    found = store.find(KEY)
    assert found is not None
    assert (found.value, found.source) == ("sk-saved", "keyring")
    assert "sk-saved" not in repr(found)
    assert KEY not in os.environ
    assert store.keyring() == "fakes MemoryKeyring"


def test_the_environment_wins_then_the_dotenv(
    store: KeyringCredentialStore,
    vault: MemoryKeyring,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    vault.set_password(SERVICE, KEY, "sk-keyring")
    monkeypatch.setenv(KEY, "sk-env")
    found = store.find(KEY)
    assert found is not None
    assert (found.value, found.source) == ("sk-env", "env")

    (tmp_path / ".env").write_text(f"{KEY}=sk-env\n")
    found = KeyringCredentialStore(dotenv=tmp_path / ".env").find(KEY)
    assert found is not None
    assert found.source == ".env"


def test_a_key_for_the_run_is_not_saved(
    store: KeyringCredentialStore, vault: MemoryKeyring
) -> None:
    vault.set_password(SERVICE, KEY, "sk-old")

    store.use(KEY, "sk-typed")

    found = store.find(KEY)
    assert found is not None
    assert (found.value, found.source) == ("sk-typed", "run")
    assert vault.passwords == {(SERVICE, KEY): "sk-old"}
    assert KEY not in os.environ


def test_remove(store: KeyringCredentialStore, vault: MemoryKeyring) -> None:
    store.save(KEY, "sk-saved")

    assert store.remove(KEY)
    assert store.find(KEY) is None
    assert vault.passwords == {}
    assert not store.remove(KEY)


def test_without_a_keyring_nothing_is_written(
    store: KeyringCredentialStore, tmp_path: Path
) -> None:
    keyring.set_keyring(fail.Keyring())

    assert store.keyring() is None
    assert store.find(KEY) is None
    with pytest.raises(KeyringUnavailable, match="no system keyring is available"):
        store.save(KEY, "sk")
    with pytest.raises(KeyringUnavailable):
        store.remove(KEY)
    assert list(tmp_path.iterdir()) == []


def test_a_locked_keyring_is_read_once(
    store: KeyringCredentialStore, monkeypatch: pytest.MonkeyPatch, vault: MemoryKeyring
) -> None:
    calls: list[str] = []

    def locked(service: str, username: str) -> str:
        calls.append(username)
        raise KeyringLocked("locked")

    monkeypatch.setattr(vault, "get_password", locked)

    assert store.find(KEY) is None
    assert store.find(KEY) is None
    assert calls == [KEY]


def test_a_chat_model_sees_a_keyring_key_only_while_built(
    store: KeyringCredentialStore, monkeypatch: pytest.MonkeyPatch
) -> None:
    seen: list[str | None] = []

    def init_chat_model(model: str, **options: Any) -> object:
        seen.append(os.environ.get(KEY))
        return object()

    monkeypatch.setattr(module, "init_chat_model", init_chat_model)
    store.save(KEY, "sk-saved")
    models = LangChainChatModels(store)

    models.build(ResolvedModel("openai", "gpt-5", "langchain-openai", "langchain_openai"))
    models.build(ResolvedModel("ollama", "qwen", "langchain-ollama", "langchain_ollama"))

    assert seen == ["sk-saved", None]
    assert KEY not in os.environ
