from dishka import Provider, Scope, provide

from ...application.ports.locale import ITranslationEngine
from ...application.ports.provider import ICredentialStore, IModelLister, IProviderCatalog
from ...infra.adapters.langchain import (
    HttpModelLister,
    LangChainChatModels,
    LangChainProviderCatalog,
)
from ...infra.adapters.langgraph import LangGraphTranslationEngine


class LangChainProvider(Provider):
    """The models: the providers LangChain knows and their models, the chat models, and the
    agents' engine."""

    scope = Scope.APP

    catalog = provide(LangChainProviderCatalog, provides=IProviderCatalog)
    chat_models = provide(LangChainChatModels)

    @provide
    def models(self, credentials: ICredentialStore) -> IModelLister:
        return HttpModelLister(credentials)

    @provide
    def engine(self, chat_models: LangChainChatModels) -> ITranslationEngine:
        return LangGraphTranslationEngine(chat_models)
