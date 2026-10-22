from abc import ABC, abstractmethod


class IPackageInstaller(ABC):
    """Installs Python packages into the environment i18n-ai runs in."""

    @abstractmethod
    async def install(self, package: str) -> None:
        """Raises `PackageInstallFailed`."""
        raise NotImplementedError
