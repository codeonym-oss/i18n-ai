from dishka import Provider, Scope, provide

from ...application.ports.provider import IPackageInstaller
from ...infra.adapters.packages import RuntimePackageInstaller


class PackagesProvider(Provider):
    """Installing a provider's package on demand."""

    scope = Scope.APP

    installer = provide(RuntimePackageInstaller, provides=IPackageInstaller)
