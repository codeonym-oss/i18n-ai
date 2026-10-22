"""What stands in for the model: a gateway that 'translates' by tagging each message with the
target, keeping its placeholders, and can be told to break some messages first; and a dishka
provider that puts it in the container, with every provider installed and no progress bar."""

import re

from dishka import Provider, Scope, provide

from i18n_ai.application.ports.locale import ITranslationEngine
from i18n_ai.application.ports.progress import IGenerationProgress
from i18n_ai.application.ports.provider import IProviderCatalog
from i18n_ai.domain.exports.locale import LocaleCode, SourceFile
from i18n_ai.infra.adapters.langchain import LangChainChatModels, LangChainProviderCatalog
from i18n_ai.infra.adapters.langgraph import (
    BatchRequest,
    FileClassification,
    LangGraphTranslationEngine,
)


class FakeGateway:
    def __init__(
        self, *, broken_first: set[str] | None = None, refuse: set[str] | None = None
    ) -> None:
        self.broken_first = (
            broken_first or set()
        )  # keys whose first translation loses its placeholders
        self.refuse = refuse or set()  # file names the classifier refuses
        self.batches: list[BatchRequest] = []
        self.classified: list[str] = []

    async def classify(self, file: SourceFile, source: LocaleCode) -> FileClassification:
        self.classified.append(str(file.name))
        refused = str(file.name) in self.refuse
        return FileClassification(qualifies=not refused, reason="fake", subject="tests")

    async def translate(self, batch: BatchRequest) -> dict[str, str]:
        self.batches.append(batch)
        target = batch.schema.target.value
        out: dict[str, str] = {}
        for unit in batch.units:
            text = f"[{target}] {unit.source}"
            if str(unit.path) in self.broken_first and unit.id not in batch.problems:
                text = re.sub(r"\{\{[^}]*\}\}", "", text)
            out[unit.id] = text
        return out


class InstalledCatalog(LangChainProviderCatalog):
    def is_installed(self, module: str) -> bool:
        return True


class SilentProgress(IGenerationProgress):
    def start(self, jobs: int) -> None: ...
    def drop(self, jobs: int, reason: str) -> None: ...
    def advance(self, description: str) -> None: ...
    def finish(self) -> None: ...


class FakeModel(Provider):
    scope = Scope.APP

    def __init__(self, gateway: FakeGateway) -> None:
        super().__init__()
        self.gateway = gateway

    @provide
    def engine(self, models: LangChainChatModels) -> ITranslationEngine:
        return LangGraphTranslationEngine(models, gateways=lambda settings: self.gateway)

    catalog = provide(InstalledCatalog, provides=IProviderCatalog)
    progress = provide(SilentProgress, provides=IGenerationProgress)
