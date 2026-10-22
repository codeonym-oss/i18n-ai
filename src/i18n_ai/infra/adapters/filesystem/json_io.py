"""Reading and writing locale JSON as its authors wrote it: the indent, the final newline,
and the characters as they are, not escaped."""

import json
import os
import re
import tempfile
from pathlib import Path
from typing import Any

from ....domain.exports.locale import JsonStyle, LocaleDocument

_INDENT = re.compile(r"^[\[{]\s*?\n([ \t]+)\S", re.MULTILINE)


def detect_style(text: str) -> JsonStyle:
    match = _INDENT.search(text.lstrip("﻿"))
    indent: int | str | None
    if match is None:
        indent = None if "\n" not in text.strip() else 2
    else:
        whitespace = match.group(1)
        indent = "\t" if "\t" in whitespace else len(whitespace)
    return JsonStyle(indent=indent, trailing_newline=text.endswith("\n"))


def read_json(path: Path) -> tuple[Any, JsonStyle]:
    """The JSON in `path`, and its style. Raises `OSError` or `ValueError`."""
    text = path.read_text(encoding="utf-8-sig")
    return json.loads(text), detect_style(text)


def load_document(path: Path) -> tuple[LocaleDocument | None, str | None]:
    """The locale document in `path`, or None and why it is not one."""
    try:
        content, style = read_json(path)
    except (OSError, ValueError) as error:
        return None, f"not valid JSON: {error}"
    if not isinstance(content, dict):
        return None, f"its top level is a {type(content).__name__}, not an object"
    return LocaleDocument(content, style), None


def dump(content: Any, style: JsonStyle) -> str:
    text = json.dumps(content, ensure_ascii=False, indent=style.indent)
    return text + "\n" if style.trailing_newline else text


def write_atomically(path: Path, text: str) -> None:
    """Write `text` to `path` through a temporary file, so a reader never sees half of it."""
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as file:
            file.write(text)
        os.replace(temporary, path)
    except BaseException:
        Path(temporary).unlink(missing_ok=True)
        raise
