from ...contract.exceptions import InfraException


class PackageInstallFailed(InfraException):
    def __init__(self, package: str, output: str) -> None:
        super().__init__(
            message=(
                f"could not install {package}:\n{output}\n"
                f"Install it yourself, e.g. `uv tool install i18n-ai --with {package}`"
            ),
            error_code="PACKAGE_INSTALL_FAILED",
            details={"package": package},
        )
