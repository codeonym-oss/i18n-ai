"""The providers' model lists, read through a transport that answers as each API would, with
the keys from the environment or the keyring."""

import asyncio
from collections.abc import Callable

import httpx
import pytest

from i18n_ai.application.ports.provider import ModelListing
from i18n_ai.infra.adapters.keyring import SERVICE, KeyringCredentialStore
from i18n_ai.infra.adapters.langchain import HttpModelLister
from support.fakes import MemoryKeyring

Handler = Callable[[httpx.Request], httpx.Response]


@pytest.fixture(autouse=True)
def keys(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GOOGLE_API_KEY", "TOGETHER_API_KEY"):
        monkeypatch.setenv(name, "key-123")
    monkeypatch.delenv("OLLAMA_HOST", raising=False)


def listing(provider: str, handler: Handler) -> ModelListing:
    lister = HttpModelLister(KeyringCredentialStore(), httpx.MockTransport(handler))
    return asyncio.run(lister.models(provider))


def ids(models: ModelListing) -> list[str]:
    return [model.id for model in models.models]


def test_openai_lists_its_chat_models() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        data = [
            {"id": "gpt-4.1-mini", "created": 2},
            {"id": "gpt-5", "created": 3},
            {"id": "text-embedding-3-small", "created": 4},
            {"id": "gpt-4o-realtime-preview", "created": 5},
            {"id": "whisper-1", "created": 6},
        ]
        return httpx.Response(200, json={"data": data})

    models = listing("openai", handler)

    assert models.live
    assert ids(models) == ["gpt-4.1-mini", "gpt-5"]
    assert models.models[1].rank == 1  # gpt-5, the second recommended
    assert models.models[0].created == 2
    assert seen[0].headers["Authorization"] == "Bearer key-123"
    assert seen[0].url.host == "api.openai.com"


def test_anthropic_tells_when_each_model_came_out() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["x-api-key"] == "key-123"
        assert request.headers["anthropic-version"]
        data = [{"id": "claude-sonnet-4-5", "created_at": "2025-09-29T00:00:00Z"}]
        return httpx.Response(200, json={"data": data})

    models = listing("anthropic", handler)

    assert ids(models) == ["claude-sonnet-4-5"]
    assert models.models[0].created == 1759104000.0


def test_google_keeps_the_models_that_generate() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["x-goog-api-key"] == "key-123"
        items = [
            {"name": "models/gemini-2.5-flash", "supportedGenerationMethods": ["generateContent"]},
            {"name": "models/text-embedding-004", "supportedGenerationMethods": ["embedContent"]},
        ]
        return httpx.Response(200, json={"models": items})

    assert ids(listing("google_genai", handler)) == ["gemini-2.5-flash"]


def test_together_answers_a_list() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=[{"id": "a", "type": "chat"}, {"id": "b", "type": "image"}])

    assert ids(listing("together", handler)) == ["a"]


def test_ollama_lists_the_local_models_without_a_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OLLAMA_HOST", "gpu-box:11434")

    def handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url) == "http://gpu-box:11434/api/tags"
        assert "Authorization" not in request.headers
        items = [{"name": "qwen2.5:14b", "modified_at": "2025-01-01T00:00:00Z"}, {"name": "x"}]
        return httpx.Response(200, json={"models": items})

    models = listing("ollama", handler)

    assert ids(models) == ["qwen2.5:14b", "x"]
    assert models.models[0].rank == 0


def test_without_a_key_the_recommended_stand_in(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY")

    models = listing("openai", lambda request: pytest.fail("no call without a key"))

    assert not models.live
    assert models.problem == "OPENAI_API_KEY is not set"
    assert ids(models)[0] == "gpt-5-mini"


def test_a_key_in_the_keyring_is_used(
    monkeypatch: pytest.MonkeyPatch, vault: MemoryKeyring
) -> None:
    monkeypatch.delenv("OPENAI_API_KEY")
    vault.set_password(SERVICE, "OPENAI_API_KEY", "key-from-keyring")

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["Authorization"] == "Bearer key-from-keyring"
        return httpx.Response(200, json={"data": [{"id": "gpt-5"}]})

    assert ids(listing("openai", handler)) == ["gpt-5"]


@pytest.mark.parametrize(
    ("status", "problem"),
    [(401, "the key was refused"), (500, "it answered 500")],
)
def test_a_refusal_is_told(status: int, problem: str) -> None:
    models = listing("openai", lambda request: httpx.Response(status, json={}))

    assert not models.live
    assert models.problem == f"openai's model list is unavailable: {problem}"


def test_no_network_is_told() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("down", request=request)

    models = listing("openai", handler)

    assert models.problem == "cannot reach api.openai.com (ConnectError)"


def test_an_unknown_answer_is_told() -> None:
    models = listing("openai", lambda request: httpx.Response(200, json={"items": []}))
    assert models.problem == "openai's model list has an unknown shape"

    models = listing("openai", lambda request: httpx.Response(200, content=b"<html>"))
    assert models.problem is not None
    assert models.problem.startswith("cannot reach")


def test_a_provider_without_a_list_gets_the_recommended() -> None:
    models = listing("perplexity", lambda request: pytest.fail("no list to call"))

    assert models.problem == "perplexity has no model list to read"
    assert ids(models) == ["sonar-pro", "sonar"]
    assert ids(listing("bedrock", lambda request: pytest.fail("no list"))) == []
