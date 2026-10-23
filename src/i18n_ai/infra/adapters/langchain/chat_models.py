import os
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any, cast

from langchain.chat_models import init_chat_model
from langchain_core.language_models import BaseChatModel

from ....application.ports.provider import ICredentialStore
from ....domain.exports.provider import ResolvedModel
from .credentials import KEYS


class LangChainChatModels:
    """Builds chat models with `init_chat_model`. Credentials come from the provider's own
    environment variables (OPENAI_API_KEY, ANTHROPIC_API_KEY, OLLAMA_HOST, ...); a key from the
    system keyring, or typed in for the run, stands in for its variable while the model is
    built, which is when every integration reads it."""

    def __init__(self, credentials: ICredentialStore) -> None:
        self._credentials = credentials

    def build(self, model: ResolvedModel, temperature: float | None = None) -> BaseChatModel:
        options: dict[str, Any] = {}
        if temperature is not None:
            options["temperature"] = temperature
        with self._key(model.provider):
            return cast(
                "BaseChatModel",
                init_chat_model(model.model, model_provider=model.provider, **options),
            )

    @contextmanager
    def _key(self, provider: str) -> Iterator[None]:
        variable = KEYS.get(provider)
        found = self._credentials.find(variable) if variable else None
        if variable is None or found is None or found.source in ("env", ".env"):
            yield
            return
        os.environ[variable] = found.value
        try:
            yield
        finally:
            del os.environ[variable]
