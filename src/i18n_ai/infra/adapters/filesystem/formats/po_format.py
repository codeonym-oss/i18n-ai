"""gettext's catalogs. An entry's key is its `msgid`, the source text itself, or its context and
`msgid` (`msgctxt` EOT `msgid`, as gettext keys them); its value is the `msgid` in a source and
the `msgstr` in a translation. A plural entry is a plural family: `{"one": msgid, "other":
msgid_plural}` in the source, its `msgstr[n]` by category in a translation.

A catalog's `Plural-Forms` numbers its forms, and is kept: which CLDR category each `msgstr[n]`
is for is read from it, so an old Russian catalog's three forms stay `one`, `few`, `many`. A new
catalog, or one whose header cannot be read, gets CLDR's numbering, in CLDR's order (`msgstr[3]`
is Arabic's `few`).

A target is the source catalog with its `msgstr` filled: its comments, references, flags and
order kept, its header's `Language`, `Plural-Forms`, `Language-Team` and `Last-Translator`
(i18n-ai) its own. An existing target keeps its own entries and header, its `PO-Revision-Date`
updated, and gets the source's new entries. A fuzzy translation is not one."""

import copy
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import polib

from .....domain.exports.locale import (
    KeyPath,
    LocaleCode,
    LocaleFormat,
    SourceFile,
)
from ..files import read_text, write_atomically
from .base import FileFormat
from .plural_forms import numbering

_CONTEXT = "\x04"


class PoFormat(FileFormat):
    format = LocaleFormat.PO
    extensions = (".po", ".pot")
    label = "PO"

    def read(self, path: Path, source: bool = False) -> Any:
        catalog, _ = _load(path)
        content: dict[str, Any] = {}
        forms_of = None if source else _numbering(catalog, catalog.metadata.get("Language", ""))
        for entry in _entries(catalog):
            if source:
                content[_key(entry)] = (
                    {"one": entry.msgid, "other": entry.msgid_plural}
                    if entry.msgid_plural
                    else entry.msgid
                )
                continue
            if entry.fuzzy:
                continue
            if not entry.msgid_plural:
                if entry.msgstr:
                    content[_key(entry)] = entry.msgstr
                continue
            forms = [entry.msgstr_plural.get(index, "") for index in range(len(forms_of or ()))]
            if forms_of and all(forms):
                # A category two forms are for is read from the first
                content[_key(entry)] = dict(reversed(list(zip(forms_of, forms, strict=True))))
        return content

    def notes(self, path: Path) -> dict[KeyPath, str]:
        catalog, _ = _load(path)
        notes = {}
        for entry in _entries(catalog):
            parts = [f"context: {entry.msgctxt}"] if entry.msgctxt else []
            if entry.comment and entry.comment.strip():
                parts.append(entry.comment.strip())
            if parts:
                notes[KeyPath((_key(entry),))] = "; ".join(parts)
        return notes

    def write(
        self,
        path: Path,
        content: dict[str, Any],
        like: SourceFile,
        key: str | None,
        locale: str | None = None,
    ) -> None:
        source, newline = _load(like.path)
        forms_of = None
        if path.is_file():
            catalog, newline = _load(path)
            forms_of = _numbering(catalog, locale or catalog.metadata.get("Language", ""))
        else:
            catalog = _new_catalog(source, locale, from_template=like.path.suffix.lower() == ".pot")
        if forms_of is None and locale is not None:
            # The tree's spelling of a locale, so a valid code
            catalog.metadata["Plural-Forms"] = LocaleCode(locale).gettext_plural_forms()
            forms_of = LocaleCode(locale).plural_categories()
        by_key = {_key(entry): entry for entry in _entries(catalog)}
        for entry in _entries(source):
            if _key(entry) not in by_key:
                added = copy.deepcopy(entry)
                added.tcomment = ""
                catalog.append(added)
                by_key[_key(entry)] = added
        for name, value in content.items():
            if name in by_key:
                _fill(by_key[name], value, forms_of)

        if locale is not None and (not path.is_file() or not catalog.metadata.get("Language")):
            catalog.metadata["Language"] = locale
        catalog.metadata["PO-Revision-Date"] = datetime.now(UTC).strftime("%Y-%m-%d %H:%M+0000")
        catalog.metadata["Content-Type"] = "text/plain; charset=UTF-8"
        catalog.encoding = "utf-8"
        text = str(catalog)
        if not catalog.header:
            text = text.removeprefix("#\n")  # polib's line for no header comment
        write_atomically(path, text.rstrip("\n") + "\n", newline)


def _new_catalog(source: polib.POFile, locale: str | None, from_template: bool) -> polib.POFile:
    """A new translation from `source`, a template or another locale's catalog: its entries,
    comments and header, with the header's translator and team its own."""
    catalog = copy.deepcopy(source)
    catalog.metadata_is_fuzzy = False
    catalog.metadata["Last-Translator"] = "i18n-ai"
    if locale is not None:
        catalog.metadata["Language-Team"] = LocaleCode(locale).display_name
    else:
        catalog.metadata.pop("Language-Team", None)
    if not from_template:
        catalog.header = ""  # "French translations of..."
    for entry in catalog:
        entry.tcomment = ""
    return catalog


def _load(path: Path) -> tuple[polib.POFile, str]:
    text, newline = read_text(path)
    try:
        # polib takes a catalog's text as well as its path; the text, so nothing is read twice
        return polib.pofile(text, encoding="utf-8"), newline
    except OSError as error:  # polib's syntax errors
        raise ValueError(str(error)) from error


def _entries(catalog: polib.POFile) -> list[polib.POEntry]:
    """The entries, the header and the obsolete ones (`#~`) left out."""
    return [entry for entry in catalog if entry.msgid and not entry.obsolete]


def _key(entry: polib.POEntry) -> str:
    return entry.msgid if entry.msgctxt is None else f"{entry.msgctxt}{_CONTEXT}{entry.msgid}"


def _numbering(catalog: polib.POFile, language: str) -> tuple[str, ...] | None:
    """The category each of a catalog's `msgstr[n]` is for, from its `Plural-Forms`; None when
    that cannot be told."""
    locale = LocaleCode.recognized(language)
    if locale is None:
        return None
    return numbering(catalog.metadata.get("Plural-Forms", ""), locale)


def _fill(entry: polib.POEntry, value: Any, forms_of: tuple[str, ...] | None) -> None:
    if entry.msgid_plural and isinstance(value, dict):
        if forms_of is None:
            entry.msgstr_plural = dict(enumerate(value.values()))
        else:
            entry.msgstr_plural = {
                index: str(value.get(category, value.get("other", "")))
                for index, category in enumerate(forms_of)
            }
    elif not entry.msgid_plural and isinstance(value, str):
        entry.msgstr = value
    else:
        return
    if "fuzzy" in entry.flags:
        entry.flags.remove("fuzzy")
    entry.previous_msgctxt = entry.previous_msgid = entry.previous_msgid_plural = None
