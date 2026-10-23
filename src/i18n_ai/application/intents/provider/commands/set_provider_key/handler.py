from mediary.cqrs import CommandHandler, command_handler

from ......domain.exports.provider import ProviderTakesNoKey
from .....ports.provider import ICredentialStore, IProviderCatalog, KeyringUnavailable
from .cmd import SetProviderKeyCommand
from .receipt import KeyReceipt


@command_handler
class SetProviderKeyCommandHandler(CommandHandler[SetProviderKeyCommand, KeyReceipt]):
    def __init__(self, providers: IProviderCatalog, credentials: ICredentialStore) -> None:
        self._providers = providers
        self._credentials = credentials

    async def handle(self, command: SetProviderKeyCommand) -> KeyReceipt:
        provider = self._providers.provider(command.provider)
        if provider.key is None:
            raise ProviderTakesNoKey(provider.name)

        problem = None
        if command.save:
            try:
                self._credentials.save(provider.key, command.key)
            except KeyringUnavailable as error:
                problem = error.message
            else:
                return self._receipt(provider.name, provider.key, saved=True)
        self._credentials.use(provider.key, command.key)
        return self._receipt(provider.name, provider.key, saved=False, problem=problem)

    def _receipt(
        self, provider: str, variable: str, saved: bool, problem: str | None = None
    ) -> KeyReceipt:
        found = self._credentials.find(variable)
        return KeyReceipt(provider, variable, saved, found.source if found else None, problem)
