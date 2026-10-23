from dataclasses import dataclass

from mediary.cqrs import Query, query

from .view import KeysView


@query
@dataclass(frozen=True)
class ListProviderKeysQuery(Query[KeysView]):
    """The system keyring, and for each provider that takes an API key, where its key comes
    from, if anywhere. Never the keys themselves."""
