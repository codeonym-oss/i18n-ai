"""Base exceptions for adapters: a general infrastructure failure, and a transient one that the
mediator's `RetryBehavior` retries, as mediary's `TransientError` is."""

from typing import Any

from mediary import TransientError


class InfraException(Exception):
    """An adapter failure. `error_code` is machine-readable, `details` gives context, and
    `cause` is the original error."""

    def __init__(
        self,
        message: str,
        error_code: str | None = None,
        details: dict[str, Any] | None = None,
        cause: Exception | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.error_code = error_code or self.__class__.__name__
        self.details = details or {}
        self.cause = cause

    def __str__(self) -> str:
        return self.message if self.cause is None else f"{self.message} - Cause: {self.cause!r}"


class TransientInfraError(InfraException, TransientError):
    """A failure that changed nothing. Running the intent again may succeed."""
