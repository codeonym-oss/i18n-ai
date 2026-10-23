from ....contract.exceptions.base import DomainException


class ProviderUnknown(DomainException):
    """A model whose provider LangChain does not know, or cannot tell from its name."""

    def __init__(self, model: str, providers: list[str]) -> None:
        super().__init__(
            message=(
                f"cannot tell the provider of {model!r}; write it as provider:model, "
                f"with one of: {', '.join(providers)}"
            ),
            error_code="PROVIDER_UNKNOWN",
            details={"model": model},
        )


class ProviderNotInstalled(DomainException):
    """The provider's LangChain package is not installed."""

    def __init__(self, provider: str, package: str) -> None:
        super().__init__(
            message=f"the {provider} provider needs {package}, which is not installed",
            error_code="PROVIDER_NOT_INSTALLED",
            details={"provider": provider, "package": package},
        )


class ProviderTakesNoKey(DomainException):
    """A provider without an API key of its own: it takes none (ollama), or several settings
    (bedrock, vertex)."""

    def __init__(self, provider: str) -> None:
        super().__init__(
            message=f"the {provider} provider takes no API key; it reads its own settings",
            error_code="PROVIDER_TAKES_NO_KEY",
            details={"provider": provider},
        )
