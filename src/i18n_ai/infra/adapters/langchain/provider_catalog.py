"""The providers LangChain's `init_chat_model` knows, read from LangChain itself so that a new
LangChain brings its new providers; a copy of the table stands in if LangChain moves it."""

import importlib
import importlib.util
import logging
import warnings
from collections.abc import Callable
from typing import Any

from ....application.ports.provider import ICredentialStore, IProviderCatalog, ProviderInfo
from ....domain.exports.provider import ModelSpec, ProviderUnknown, ResolvedModel
from .credentials import KEYS

logger = logging.getLogger(__name__)

# provider -> the module its chat model is imported from (langchain 1.x's `_BUILTIN_PROVIDERS`)
_FALLBACK = {
    "anthropic": "langchain_anthropic",
    "anthropic_bedrock": "langchain_aws",
    "azure_ai": "langchain_azure_ai.chat_models",
    "azure_openai": "langchain_openai",
    "baseten": "langchain_baseten",
    "bedrock": "langchain_aws",
    "bedrock_converse": "langchain_aws",
    "cohere": "langchain_cohere",
    "deepseek": "langchain_deepseek",
    "fireworks": "langchain_fireworks",
    "google_anthropic_vertex": "langchain_google_vertexai.model_garden",
    "google_genai": "langchain_google_genai",
    "google_vertexai": "langchain_google_vertexai",
    "groq": "langchain_groq",
    "huggingface": "langchain_huggingface",
    "ibm": "langchain_ibm",
    "litellm": "langchain_litellm",
    "mistralai": "langchain_mistralai",
    "nvidia": "langchain_nvidia_ai_endpoints",
    "ollama": "langchain_ollama",
    "openai": "langchain_openai",
    "openrouter": "langchain_openrouter",
    "perplexity": "langchain_perplexity",
    "together": "langchain_together",
    "upstage": "langchain_upstage",
    "xai": "langchain_xai",
}


class LangChainProviderCatalog(IProviderCatalog):
    def __init__(self, credentials: ICredentialStore) -> None:
        self._credentials = credentials
        self._modules, self._infer = _langchain_table()

    def providers(self) -> list[ProviderInfo]:
        return [self.provider(name) for name in self._modules]

    def provider(self, name: str) -> ProviderInfo:
        key = name.replace("-", "_").lower()
        module = self._modules.get(key)
        if module is None:
            raise ProviderUnknown(name, sorted(self._modules))
        root = module.split(".", 1)[0]
        variable = KEYS.get(key)
        found = self._credentials.find(variable) if variable else None
        return ProviderInfo(
            name=key,
            package=root.replace("_", "-"),
            module=root,
            installed=self.is_installed(root),
            key=variable,
            key_source=found.source if found else None,
        )

    def resolve(self, spec: ModelSpec) -> ResolvedModel:
        value = spec.value
        provider: str | None = None
        model = value
        prefix, separator, rest = value.partition(":")
        if separator and prefix.replace("-", "_").lower() in self._modules:
            provider, model = prefix, rest
        elif self._infer is not None:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                provider = self._infer(value)
        if provider is None or not model:
            raise ProviderUnknown(value, sorted(self._modules))
        info = self.provider(provider)
        return ResolvedModel(
            provider=info.name, model=model, package=info.package, module=info.module
        )

    def is_installed(self, module: str) -> bool:
        importlib.invalidate_caches()
        try:
            return importlib.util.find_spec(module) is not None
        except (ImportError, ValueError):
            return False


def _langchain_table() -> tuple[dict[str, str], Callable[[str], str | None] | None]:
    try:
        base: Any = importlib.import_module("langchain.chat_models.base")
    except ImportError:  # pragma: no cover - langchain is a dependency
        return dict(_FALLBACK), None
    table = getattr(base, "_BUILTIN_PROVIDERS", None)
    infer = getattr(base, "_attempt_infer_model_provider", None)
    if not isinstance(table, dict):
        logger.debug("LangChain has no _BUILTIN_PROVIDERS; using i18n-ai's copy")
        return dict(_FALLBACK), infer
    modules = {
        name: entry[0] for name, entry in table.items() if isinstance(entry, tuple) and entry
    }
    return modules or dict(_FALLBACK), infer
