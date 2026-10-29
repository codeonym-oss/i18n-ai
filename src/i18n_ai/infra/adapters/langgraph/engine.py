from collections.abc import AsyncIterator, Callable
from typing import Any, cast

from langchain_core.runnables import RunnableConfig

from ....application.ports.locale import (
    AtomStarted,
    AttemptRejected,
    EngineEvent,
    EngineRequest,
    EngineSettings,
    ITranslationEngine,
)
from ..langchain.chat_models import LangChainChatModels
from .gateway import ILlmGateway, LangChainGateway
from .graph import RunState, build_run_graph

GatewayFactory = Callable[[EngineSettings], ILlmGateway]


class LangGraphTranslationEngine(ITranslationEngine):
    """Runs the agents' graph (see `graph`) and streams its events as each node finishes, so a
    file is written as soon as it is translated, and its atom's start and retries as they
    happen."""

    def __init__(self, models: LangChainChatModels, gateways: GatewayFactory | None = None) -> None:
        self._models = models
        self._gateways = gateways or self._langchain_gateway

    async def run(self, request: EngineRequest) -> AsyncIterator[EngineEvent]:
        settings = request.settings
        graph = build_run_graph(self._gateways(settings))
        state: RunState = {"request": request, "classified": [], "outcomes": []}
        config = RunnableConfig(max_concurrency=max(2, settings.concurrency * 2))
        # The atoms write their start and their retries from inside, through the subgraphs;
        # their own node updates are theirs, and only the run's are events
        async for item in graph.astream(
            state, config, stream_mode=["updates", "custom"], subgraphs=True
        ):
            namespace, mode, chunk = cast(tuple[tuple[str, ...], str, Any], item)
            if mode == "custom":
                if isinstance(chunk, AtomStarted | AttemptRejected):
                    yield chunk
                continue
            if namespace:
                continue
            for delta in chunk.values():
                if not delta:
                    continue
                for event in delta.get("classified", []):
                    yield event
                for event in delta.get("outcomes", []):
                    yield event

    def _langchain_gateway(self, settings: EngineSettings) -> ILlmGateway:
        model = self._models.build(settings.model, settings.temperature)
        return LangChainGateway(model, settings.concurrency)
