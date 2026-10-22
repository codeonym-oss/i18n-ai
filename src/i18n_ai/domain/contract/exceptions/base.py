from typing import Any


class DomainException(Exception):
    """Base class for all domain exceptions.

    - `message`: human-readable error message.
    - `error_code`: machine-readable error code.
    - `details`: more context about the error."""

    def __init__(
        self, message: str, error_code: str | None = None, details: dict[str, Any] | None = None
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code or self.__class__.__name__
        self.details = details or {}

    def to_dict(self) -> dict[str, Any]:
        return {"error_code": self.error_code, "message": self.message, "details": self.details}

    def __str__(self) -> str:
        return self.message
