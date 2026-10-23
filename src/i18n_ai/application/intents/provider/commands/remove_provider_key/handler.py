from mediary.cqrs import CommandHandler, command_handler

from ......domain.exports.provider import ProviderTakesNoKey
from .....ports.provider import ICredentialStore, IProviderCatalog
from .cmd import RemoveProviderKeyCommand
from .receipt import KeyRemoval


@command_handler
class RemoveProviderKeyCommandHandler(CommandHandler[RemoveProviderKeyCommand, KeyRemoval]):
    def __init__(self, providers: IProviderCatalog, credentials: ICredentialStore) -> None:
        self._providers = providers
        self._credentials = credentials

    async def handle(self, command: RemoveProviderKeyCommand) -> KeyRemoval:
        provider = self._providers.provider(command.provider)
        if provider.key is None:
            raise ProviderTakesNoKey(provider.name)
        removed = self._credentials.remove(provider.key)
        found = self._credentials.find(provider.key)
        return KeyRemoval(provider.name, provider.key, removed, found.source if found else None)
