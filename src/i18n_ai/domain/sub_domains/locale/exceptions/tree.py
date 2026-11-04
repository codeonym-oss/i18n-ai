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


class PresetUnknown(DomainException):
    """No preset has the name asked."""

    def __init__(self, name: str, known: list[str]) -> None:
        super().__init__(
            message=f"no preset is called {name}; the presets are {', '.join(known)}",
            error_code="PRESET_UNKNOWN",
            details={"name": name},
        )


class MessageUnknown(DomainException):
    """A path is no message of a source file's translation into a target."""

    def __init__(self, file: str, target: str, path: str) -> None:
        super().__init__(
            message=f"{path} is no message of {file} in {target}",
            error_code="MESSAGE_UNKNOWN",
            details={"file": file, "target": target, "path": path},
        )


class TargetNotGenerated(DomainException):
    """A target has no version of a source file yet, so it has no message to set."""

    def __init__(self, file: str, target: str) -> None:
        super().__init__(
            message=f"{target} has no version of {file} yet; generate it first",
            error_code="TARGET_NOT_GENERATED",
            details={"file": file, "target": target},
        )
