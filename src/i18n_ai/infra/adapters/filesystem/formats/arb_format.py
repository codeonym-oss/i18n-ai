"""Flutter's Application Resource Bundle: JSON whose messages are ICU MessageFormat, beside
entries that are not messages. `@@locale` and the other `@@` globals describe the file; `@key`
describes `key` for its translators and for `gen-l10n` (its description, its placeholders' types).

A target has the source's globals, `@@locale` its own locale, and its messages in the source's
order. The `@key` entries are read from the template file only, so a target keeps the ones it
has and gets none from the source."""

from pathlib import Path
from typing import Any

from .....domain.exports.locale import LocaleFormat, SourceFile
from ..files import write_atomically
from .base import FileFormat
from .json_format import JsonStyle, dump, read_json


class ArbFormat(FileFormat):
    format = LocaleFormat.ARB
    extensions = (".arb",)
    label = "ARB"

    def read(self, path: Path) -> Any:
        content, _ = read_json(path)
        if not isinstance(content, dict):
            return content
        return {key: value for key, value in content.items() if not key.startswith("@")}

    def write(
        self,
        path: Path,
        content: dict[str, Any],
        like: SourceFile,
        key: str | None,
        locale: str | None = None,
    ) -> None:
        source, style = _read(like.path)
        existing, _ = _read(path) if path.is_file() else ({}, style)

        document: dict[str, Any] = {}
        for name, value in source.items():
            if name.startswith("@@"):
                document[name] = locale if name == "@@locale" and locale else value
        for name, value in content.items():
            document[name] = value
            if f"@{name}" in existing:
                document[f"@{name}"] = existing[f"@{name}"]
        write_atomically(path, dump(document, style), style.newline)


def _read(path: Path) -> tuple[dict[str, Any], JsonStyle]:
    try:
        content, style = read_json(path)
    except (OSError, ValueError):
        return {}, JsonStyle()
    return (content if isinstance(content, dict) else {}), style
