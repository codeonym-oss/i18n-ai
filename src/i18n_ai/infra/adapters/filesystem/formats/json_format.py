"""Locale JSON as its authors wrote it: the indent, the final newline, the line endings, and the
characters as they are, not escaped."""

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .....domain.exports.locale import LocaleFormat, SourceFile
from ..files import read_text, write_atomically
from .base import FileFormat

_INDENT = re.compile(r"^[\[{]\s*?\n([ \t]+)\S", re.MULTILINE)


@dataclass(frozen=True)
class JsonStyle:
    """How a JSON file is written: the indent (spaces, a tab, or None for one line), a newline
    at the end, and the line ending."""

    indent: int | str | None = 2
    trailing_newline: bool = True
    newline: str = "\n"


def detect_style(text: str, newline: str = "\n") -> JsonStyle:
    match = _INDENT.search(text.lstrip("﻿"))
    indent: int | str | None
    if match is None:
        indent = None if "\n" not in text.strip() else 2
    else:
        whitespace = match.group(1)
        indent = "\t" if "\t" in whitespace else len(whitespace)
    return JsonStyle(indent, text.endswith("\n"), newline)


def read_json(path: Path) -> tuple[Any, JsonStyle]:
    """The JSON in `path`, and its style. Raises `OSError` or `ValueError`."""
    text, newline = read_text(path)
    return json.loads(text), detect_style(text, newline)


def dump(content: Any, style: JsonStyle) -> str:
    text = json.dumps(content, ensure_ascii=False, indent=style.indent)
    return text + "\n" if style.trailing_newline else text


class JsonFormat(FileFormat):
    format = LocaleFormat.JSON
    extensions = (".json",)
    label = "JSON"

    def read(self, path: Path) -> Any:
        content, _ = read_json(path)
        return content

    def write(self, path: Path, content: dict[str, Any], like: SourceFile, key: str | None) -> None:
        try:
            _, style = read_json(like.path)
        except (OSError, ValueError):
            style = JsonStyle()
        document: Any = content
        if key is not None:
            # Under its key, the file keeps its other keys, its order and its own style
            document = {}
            if path.is_file():
                existing, style = read_json(path)
                if isinstance(existing, dict):
                    document = existing
            document[key] = content
        write_atomically(path, dump(document, style), style.newline)
