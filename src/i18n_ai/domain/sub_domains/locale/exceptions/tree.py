from ....contract.exceptions.base import DomainException


class LocaleTreeNotFound(DomainException):
    """The path holds no locale tree: no locale directory, no locale file, no bundle."""

    def __init__(self, path: str, reason: str) -> None:
        super().__init__(
            message=f"no locale tree at {path}: {reason}",
            error_code="LOCALE_TREE_NOT_FOUND",
            details={"path": path},
        )


class SourceLocaleUnknown(DomainException):
    """The tree has several locales and none is named as the source, or not the one named."""

    def __init__(self, path: str, found: list[str], asked: str | None = None) -> None:
        locales = ", ".join(found)
        super().__init__(
            message=(
                f"{path} has no {asked} locale; it holds {locales}"
                if asked
                else f"{path} holds the locales {locales}; name the source one with --source"
            ),
            error_code="SOURCE_LOCALE_UNKNOWN",
            details={"path": path, "found": found},
        )


class TargetIsSource(DomainException):
    """A target locale is the source locale itself."""

    def __init__(self, locale: str) -> None:
        super().__init__(
            message=f"{locale} is the source locale; it cannot be generated from itself",
            error_code="TARGET_IS_SOURCE",
            details={"locale": locale},
        )


class MixedLocaleFormats(DomainException):
    """The source's files are in several formats, and none was chosen."""

    def __init__(self, path: str, formats: list[str]) -> None:
        super().__init__(
            message=(
                f"{path} mixes the formats {', '.join(formats)}; "
                "choose the one to translate with --format"
            ),
            error_code="MIXED_LOCALE_FORMATS",
            details={"path": path, "formats": formats},
        )
