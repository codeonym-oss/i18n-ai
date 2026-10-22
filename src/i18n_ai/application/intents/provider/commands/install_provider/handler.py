import logging

from mediary.cqrs import CommandHandler, command_handler

from ......domain.exports.provider import ProviderNotInstalled
from .....ports.provider import IPackageInstaller, IProviderCatalog
from .cmd import InstallProviderCommand
from .receipt import InstallReceipt

logger = logging.getLogger(__name__)


@command_handler
class InstallProviderCommandHandler(CommandHandler[InstallProviderCommand, InstallReceipt]):
    """Install the provider's package into the running environment, then check that it imports."""

    def __init__(self, providers: IProviderCatalog, installer: IPackageInstaller) -> None:
        self._providers = providers
        self._installer = installer

    async def handle(self, command: InstallProviderCommand) -> InstallReceipt:
        provider = self._providers.provider(command.provider)
        if provider.installed:
            return InstallReceipt(provider.name, provider.package, installed_now=False)

        logger.info("Installing %s for the %s provider", provider.package, provider.name)
        await self._installer.install(provider.package)
        if not self._providers.is_installed(provider.module):
            raise ProviderNotInstalled(provider.name, provider.package)
        return InstallReceipt(provider.name, provider.package, installed_now=True)
