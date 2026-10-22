from typing import Any, cast

from langchain.chat_models import init_chat_model
from langchain_core.language_models import BaseChatModel

from ....domain.exports.provider import ResolvedModel


class LangChainChatModels:
    """Builds chat models with `init_chat_model`. Credentials come from the provider's own
    environment variables (OPENAI_API_KEY, ANTHROPIC_API_KEY, OLLAMA_HOST, ...)."""

    def build(self, model: ResolvedModel, temperature: float | None = None) -> BaseChatModel:
        options: dict[str, Any] = {}
        if temperature is not None:
            options["temperature"] = temperature
        return cast(
            "BaseChatModel", init_chat_model(model.model, model_provider=model.provider, **options)
        )
