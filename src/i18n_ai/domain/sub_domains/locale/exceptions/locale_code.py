from ....contract.exceptions.base import DomainException


class InvalidLocaleCode(DomainException):
    """A code that is not a locale, such as `english` or `e_n`."""

    def __init__(self, value: str) -> None:
        super().__init__(
            message=f"{value!r} is not a locale code (expected one like en, fr, pt-BR or zh_Hant)",
            error_code="INVALID_LOCALE_CODE",
            details={"value": value},
        )
