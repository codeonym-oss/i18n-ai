"""The locale file formats, one adapter each, found by a file's extension."""

from pathlib import Path

from .....domain.exports.locale import LocaleDocument, LocaleFormat
from .arb_format import ArbFormat
from .base import FileFormat
from .json_format import JsonFormat
from .yaml_format import YamlFormat

FORMATS: dict[LocaleFormat, FileFormat] = {
    adapter.format: adapter for adapter in (JsonFormat(), YamlFormat(), ArbFormat())
}


def format_of(path: Path) -> FileFormat | None:
    """The format of `path`, by its extension, if i18n-ai reads it."""
    suffix = path.suffix.lower()
    return next((adapter for adapter in FORMATS.values() if suffix in adapter.extensions), None)


def extensions(only: LocaleFormat | None = None) -> tuple[str, ...]:
    """The extensions of `only`, or of every format."""
    adapters = [FORMATS[only]] if only is not None else FORMATS.values()
    return tuple(extension for adapter in adapters for extension in adapter.extensions)


def load_document(path: Path, adapter: FileFormat) -> tuple[LocaleDocument | None, str | None]:
    """The locale document in `path`, or None and why it is not one."""
    try:
        content = adapter.read(path)
    except (OSError, ValueError) as error:
        return None, f"not valid {adapter.label}: {error}"
    if not isinstance(content, dict):
        kind = "nothing" if content is None else f"a {type(content).__name__}"
        return None, f"its top level is {kind}, not an object"
    return LocaleDocument(content), None


__all__ = ["FORMATS", "FileFormat", "extensions", "format_of", "load_document"]
