from .base import DomainException


class EmptyValueProvided(DomainException):
    """A value that must be given was empty."""

    def __init__(self, name: str) -> None:
        super().__init__(
            message=f"{name} must not be empty", error_code="EMPTY_VALUE", details={"field": name}
        )


class InvalidValueProvided(DomainException):
    """A value that breaks its own rules."""

    def __init__(self, name: str, reason: str) -> None:
        super().__init__(
            message=f"{name}: {reason}", error_code="INVALID_VALUE", details={"field": name}
        )
