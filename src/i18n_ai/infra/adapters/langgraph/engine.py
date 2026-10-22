from collections.abc import AsyncIterator, Callable

from langchain_core.runnables import RunnableConfig

from ....application.ports.locale import (
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
    file is written as soon as it is translated."""

    def __init__(self, models: LangChainChatModels, gateways: GatewayFactory | None = None) -> None:
        self._models = models
        self._gateways = gateways or self._langchain_gateway

    async def run(self, request: EngineRequest) -> AsyncIterator[EngineEvent]:
        settings = request.settings
        graph = build_run_graph(self._gateways(settings))
        state: RunState = {"request": request, "classified": [], "outcomes": []}
        config = RunnableConfig(max_concurrency=max(2, settings.concurrency * 2))
        async for update in graph.astream(state, config, stream_mode="updates"):
            for delta in update.values():
                if not delta:
                    continue
                for event in delta.get("classified", []):
                    yield event
                for event in delta.get("outcomes", []):
                    yield event

    def _langchain_gateway(self, settings: EngineSettings) -> ILlmGateway:
        model = self._models.build(settings.model, settings.temperature)
        return LangChainGateway(model, settings.concurrency)
