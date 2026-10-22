from dataclasses import dataclass

from mediary.cqrs import Command, command

from .receipt import InstallReceipt


@command
@dataclass(frozen=True)
class InstallProviderCommand(Command[InstallReceipt]):
    """Install a provider's LangChain package, unless it is installed already. Raises
    `ProviderUnknown`, `PackageInstallFailed`, or `ProviderNotInstalled` when the package
    installed but cannot be imported."""

    provider: str
