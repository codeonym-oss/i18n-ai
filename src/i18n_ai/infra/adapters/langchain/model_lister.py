"""The models a provider serves, read from its API's model list, which costs nothing and generates
nothing; the models i18n-ai recommends for translating stand in when the list cannot be read
(no key, no network, or no such endpoint)."""

import logging
import os
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal

import httpx

from ....application.ports.provider import ICredentialStore, IModelLister, ModelInfo, ModelListing
from .credentials import KEYS

logger = logging.getLogger(__name__)

Item = dict[str, Any]

# The models to try first, best first. Kept short: the API's list shows the rest.
_RECOMMENDED: dict[str, tuple[str, ...]] = {
    "anthropic": ("claude-sonnet-5-5", "claude-haiku-5-5", "claude-opus-5-5", "claude-sonnet-4-5"),
    "cohere": ("command-a-03-2025",),
    "deepseek": ("deepseek-chat",),
    "fireworks": ("accounts/fireworks/models/llama-v3p3-70b-instruct",),
    "google_genai": ("gemini-2.5-flash", "gemini-2.5-pro"),
    "groq": ("llama-3.3-70b-versatile", "openai/gpt-oss-120b"),
    "mistralai": ("mistral-large-latest", "mistral-medium-latest", "mistral-small-latest"),
    "ollama": ("qwen2.5:14b", "gemma3:12b", "llama3.1:8b"),
    "openai": ("gpt-5-mini", "gpt-5", "gpt-4.1-mini", "gpt-4.1"),
    "openrouter": ("openai/gpt-4.1-mini", "anthropic/claude-sonnet-4.5", "google/gemini-2.5-flash"),
    "perplexity": ("sonar-pro", "sonar"),
    "together": ("meta-llama/Llama-3.3-70B-Instruct-Turbo",),
    "xai": ("grok-4", "grok-3-mini"),
}


def _created(item: Item) -> float | None:
    value = item.get("created", item.get("created_at", item.get("modified_at")))
    if isinstance(value, int | float):
        return float(value)
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()
        except ValueError:
            return None
    return None


def _none_of(*words: str) -> Callable[[str], bool]:
    return lambda model: not any(word in model for word in words)


_OPENAI_CHAT = _none_of(
    "audio", "realtime", "tts", "transcribe", "image", "search", "embedding", "moderation",
    "instruct",
)  # fmt: skip


@dataclass(frozen=True)
class _Api:
    """A provider's model list: where it is, how to authenticate, where its items are (None:
    the answer is the list), each item's id, and which items are chat models."""

    url: str
    auth: Literal["bearer", "anthropic", "google", "none"] = "bearer"
    items: str | None = "data"
    id: str = "id"
    chat: Callable[[Item], bool] = lambda item: True
    keyed: bool = True


_APIS: dict[str, _Api] = {
    "anthropic": _Api("https://api.anthropic.com/v1/models?limit=1000", auth="anthropic"),
    "cohere": _Api(
        "https://api.cohere.com/v1/models?endpoint=chat&page_size=1000", items="models", id="name"
    ),
    "deepseek": _Api("https://api.deepseek.com/models"),
    "google_genai": _Api(
        "https://generativelanguage.googleapis.com/v1beta/models?pageSize=1000",
        auth="google",
        items="models",
        id="name",
        chat=lambda item: (
            "generateContent" in item.get("supportedGenerationMethods", [])
            and _none_of("embedding", "tts", "image")(str(item.get("name")))
        ),
    ),
    "groq": _Api(
        "https://api.groq.com/openai/v1/models",
        chat=lambda item: _none_of("whisper", "tts", "guard", "playai")(str(item.get("id"))),
    ),
    "mistralai": _Api(
        "https://api.mistral.ai/v1/models",
        chat=lambda item: bool(item.get("capabilities", {}).get("completion_chat", True)),
    ),
    "ollama": _Api("{ollama}/api/tags", auth="none", items="models", id="name", keyed=False),
    "openai": _Api(
        "https://api.openai.com/v1/models",
        chat=lambda item: (
            str(item.get("id")).startswith(("gpt-", "o1", "o3", "o4", "chatgpt-"))
            and _OPENAI_CHAT(str(item.get("id")))
        ),
    ),
    "openrouter": _Api("https://openrouter.ai/api/v1/models", auth="none", keyed=False),
    "together": _Api(
        "https://api.together.xyz/v1/models",
        items=None,
        chat=lambda item: item.get("type") == "chat",
    ),
    "xai": _Api("https://api.x.ai/v1/models"),
}


class HttpModelLister(IModelLister):
    """`transport` replaces the network, in tests."""

    def __init__(
        self, credentials: ICredentialStore, transport: httpx.AsyncBaseTransport | None = None
    ) -> None:
        self._credentials = credentials
        self._transport = transport

    async def models(self, provider: str) -> ModelListing:
        recommended = _RECOMMENDED.get(provider, ())
        api = _APIS.get(provider)
        if api is None:
            return _fallback(recommended, f"{provider} has no model list to read")
        found = self._credentials.find(KEYS[provider]) if provider in KEYS else None
        key = found.value if found else None
        if api.keyed and key is None:
            return _fallback(recommended, f"{KEYS[provider]} is not set")

        url = api.url.format(ollama=_ollama_host())
        try:
            async with httpx.AsyncClient(transport=self._transport, timeout=10) as client:
                response = await client.get(url, headers=_headers(api, key))
                response.raise_for_status()
                payload = response.json()
        except httpx.HTTPStatusError as error:
            status = error.response.status_code
            reason = "the key was refused" if status in (401, 403) else f"it answered {status}"
            return _fallback(recommended, f"{provider}'s model list is unavailable: {reason}")
        except (httpx.HTTPError, ValueError) as error:
            logger.debug("Listing %s's models failed", provider, exc_info=True)
            host = httpx.URL(url).host
            return _fallback(recommended, f"cannot reach {host} ({type(error).__name__})")

        items = payload.get(api.items) if api.items and isinstance(payload, dict) else payload
        if not isinstance(items, list):
            return _fallback(recommended, f"{provider}'s model list has an unknown shape")
        models = []
        for item in items:
            if not isinstance(item, dict) or not api.chat(item):
                continue
            model = str(item.get(api.id, "")).removeprefix("models/")
            if model:
                rank = recommended.index(model) if model in recommended else None
                models.append(ModelInfo(model, _created(item), rank))
        return ModelListing(tuple(models), live=True)


def _headers(api: _Api, key: str | None) -> dict[str, str]:
    if key is None or api.auth == "none":
        return {}
    if api.auth == "anthropic":
        return {"x-api-key": key, "anthropic-version": "2023-06-01"}
    if api.auth == "google":
        return {"x-goog-api-key": key}
    return {"Authorization": f"Bearer {key}"}


def _ollama_host() -> str:
    host = os.environ.get("OLLAMA_HOST") or "http://localhost:11434"
    return (host if "://" in host else f"http://{host}").rstrip("/")


def _fallback(recommended: tuple[str, ...], problem: str) -> ModelListing:
    models = tuple(ModelInfo(model, rank=rank) for rank, model in enumerate(recommended))
    return ModelListing(models, live=False, problem=problem)
