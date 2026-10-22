from enum import StrEnum


class TreeLayout(StrEnum):
    """How a tree lays its locales out.

    - `directory`: one directory per locale, holding any number of files (`locales/en/common.json`).
    - `file`: one file per locale (`messages/en.json`).
    - `bundle`: one file holding every locale under its code (`{"en": {...}, "fr": {...}}`)."""

    DIRECTORY = "directory"
    FILE = "file"
    BUNDLE = "bundle"
