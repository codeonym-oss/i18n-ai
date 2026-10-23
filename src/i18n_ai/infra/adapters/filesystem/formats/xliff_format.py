"""XLIFF, the XML that Angular, Symfony and translation tools exchange, in its versions 1.2
(`<trans-unit>`) and 2.0 (`<unit>` and its `<segment>`s). A message's key is its unit's `id`,
and its segment's when the unit has several (`id#2`); its value is the unit's `<source>`, or its
`<target>` in a translation. A source-only file is a template (Angular's `messages.xlf`); in a
source locale's own file, as Symfony writes them, a message's text is its `<target>`.

The inline elements, a placeholder or a run of bold, are given to the model as tags it keeps:
`<x1/>` for one whose content is code or nothing (1.2's `<x/>` and `<ph>`, 2.0's `<ph/>`), and
`<g2>...</g2>` around the text of one that holds text (`<g>`, `<pc>`, `<mrk>`). Each is numbered
by its place in the source, so a translation may move it, and is written back as it was. What a
tag stands for, when the file says it (Angular's `equiv-text` and `disp`), is in the message's
note, with its `<note>`s.

A target is the source file with its `<target>`s filled, each marked as a machine's, for a
translator to review (see `_MACHINE_1`), and its `target-language` (1.2) or `trgLang` (2.0) its
own. An existing target keeps its own units and
what is around them, its translations as they are, and gets the source's new units and current
`<source>`s."""

import copy
import re
from collections import Counter
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from lxml import etree

from .....domain.exports.locale import KeyPath, LocaleFormat, SourceFile
from ..files import read_text, write_atomically
from .base import FileFormat

_DECLARATION = re.compile(r"^\s*(<\?xml[^>]*\?>)\s*")
_ENCODING = re.compile(r"""encoding\s*=\s*["'][^"']*["']""")
_TOKEN = re.compile(r"<(/?)([xg])(\d+)(/?)>")
# The inline elements whose content is text to translate; the others' is code, or nothing
_PAIRED = frozenset({"g", "mrk", "pc"})
# A target in these states is not a translation yet
_UNTRANSLATED = frozenset({"new", "needs-translation", "initial"})
# How a machine's translation is marked: 1.2 has a state for it to be reviewed, and a qualifier
# for machine translation; 2.0's states have neither, so its `subState` says it, for the tools
# that filter on it. A translation so marked is one: it is not translated again.
_MACHINE_1 = {"state": "needs-review-translation", "state-qualifier": "mt-suggestion"}
_MACHINE_2 = {"state": "translated", "subState": "i18n-ai:mt"}
# Where 2.0's notes say where a message is used, which is no help to its translator
_SKIPPED_NOTES = frozenset({"location"})

type _Key = tuple[str, str]


@dataclass(frozen=True)
class _Message:
    """A unit's message: its key, its unit, and what holds its `<source>` and `<target>` (the
    unit in 1.2, the segment in 2.0)."""

    key: str
    unit: etree._Element
    holder: etree._Element
    two: bool

    @property
    def source(self) -> etree._Element | None:
        return _child(self.holder, "source")

    @property
    def target(self) -> etree._Element | None:
        return _child(self.holder, "target")

    @property
    def state(self) -> str | None:
        element = self.holder if self.two else self.target
        return element.get("state") if element is not None else None

    def text(self, source: bool) -> etree._Element | None:
        """The element holding the message's text: its translation, or as a source's, its
        `<target>` when it has one and else its `<source>`."""
        target = self.target
        translated = (
            target is not None
            and (bool(target.text) or len(target) > 0)
            and self.state not in _UNTRANSLATED
        )
        if translated:
            return target
        return self.source if source else None


class XliffFormat(FileFormat):
    format = LocaleFormat.XLIFF
    extensions = (".xlf", ".xliff")
    label = "XLIFF"

    def read(self, path: Path, source: bool = False) -> Any:
        tree, _ = _parse(path)
        content: dict[str, Any] = {}
        for message in _messages(tree.getroot()):
            text = _translation(message, source)
            if text is not None and message.key not in content:
                content[message.key] = text
        return content

    def notes(self, path: Path) -> dict[KeyPath, str]:
        tree, _ = _parse(path)
        notes = {}
        for message in _messages(tree.getroot()):
            text, original = message.text(source=True), message.source
            if text is None or original is None:
                continue
            table = _Table(original, text)
            parts = []
            name = message.unit.get("resname") or message.unit.get("name")
            if name and name != _flatten(text, table):
                parts.append(f"key: {name}")
            parts.extend(_notes(message))
            tags = table.meanings()
            if tags:
                parts.append("tags: " + ", ".join(tags))
            if parts:
                notes[KeyPath((message.key,))] = "; ".join(parts)
        return notes

    def write(
        self,
        path: Path,
        content: dict[str, Any],
        like: SourceFile,
        key: str | None,
        locale: str | None = None,
    ) -> None:
        source, _ = _parse(like.path)
        exists = path.is_file()
        tree, newline = _parse(path) if exists else _parse(like.path)
        root = tree.getroot()
        if not exists:
            for message in _messages(root):
                if message.target is not None:
                    message.holder.remove(message.target)
                if message.two:
                    message.holder.attrib.pop("state", "")
        _add_new_units(source.getroot(), root)

        originals = {message.key: message for message in _messages(source.getroot())}
        for message in _messages(root):
            value = content.get(message.key)
            original = originals.get(message.key)
            if not isinstance(value, str) or original is None or original.source is None:
                continue
            if _translation(message) == value:
                continue  # kept as it is, its state too
            text = original.text(source=True)
            assert text is not None
            _replace(message.holder, message.source, copy.deepcopy(original.source))
            _fill(_target(message), value, _Table(original.source, text))
            marked = message.holder if message.two else _target(message)
            for name, value in (_MACHINE_2 if message.two else _MACHINE_1).items():
                marked.set(name, value)

        if locale is not None:
            if _two(root):
                if not exists or not root.get("trgLang"):
                    root.set("trgLang", locale)
            else:
                for file in _children(root, "file"):
                    if not exists or not file.get("target-language"):
                        file.set("target-language", locale)
        write_atomically(path, _serialize(tree, path if exists else like.path), newline)


def _translation(message: _Message, source: bool = False) -> str | None:
    """The message's text (see `_Message.text`), its tags numbered."""
    text = message.text(source)
    if text is None or message.source is None:
        return None
    return _flatten(text, _Table(message.source, text))


class _Table:
    """The inline elements of a message, numbered: its source's, in their order, then any its
    text has that its source has not. An element is known by its name and `id` (or its place
    among the elements of its name), so a translation's are numbered as its source's."""

    def __init__(self, *elements: etree._Element) -> None:
        self.number: dict[_Key, int] = {}
        self.elements: list[etree._Element] = []
        for element in elements:
            for key, inline in _keyed(element):
                if key not in self.number:
                    self.elements.append(inline)
                    self.number[key] = len(self.elements)

    def meanings(self) -> list[str]:
        """What each tag stands for, where the file says it: `<x1/> is {{ name }}`."""
        meanings = []
        for number, element in enumerate(self.elements, 1):
            if _local(element) in _PAIRED:
                start = element.get("dispStart") or element.get("equivStart")
                end = element.get("dispEnd") or element.get("equivEnd")
                if start and end:
                    meanings.append(f"<g{number}>…</g{number}> is {start}…{end}")
                continue
            meaning = element.get("equiv-text") or element.get("disp") or element.get("equiv")
            if meaning is None and len(element) == 0 and element.text:
                meaning = element.text  # 1.2's `<ph>` and `<bpt>` hold their code
            if meaning:
                meanings.append(f"<x{number}/> is {meaning}")
        return meanings


def _keyed(element: etree._Element) -> Iterator[tuple[_Key, etree._Element]]:
    """The inline elements in `element`, in document order, each with its key."""
    seen: Counter[str] = Counter()

    def walk(parent: etree._Element) -> Iterator[tuple[_Key, etree._Element]]:
        for child in _elements(parent):
            name = _local(child)
            identity = child.get("id") or child.get("startRef") or f"#{seen[name]}"
            seen[name] += 1
            yield (name, identity), child
            if name in _PAIRED:
                yield from walk(child)

    return walk(element)


def _flatten(element: etree._Element, table: _Table) -> str:
    """`element`'s text, its inline elements as the table numbers them."""
    numbers = iter([table.number[key] for key, _ in _keyed(element)])

    def text_of(parent: etree._Element) -> str:
        parts = [parent.text or ""]
        for child in parent:
            if isinstance(child.tag, str):  # not a comment
                number = next(numbers)
                if _local(child) in _PAIRED:
                    parts.append(f"<g{number}>{text_of(child)}</g{number}>")
                else:
                    parts.append(f"<x{number}/>")
            parts.append(child.tail or "")
        return "".join(parts)

    return text_of(element)


def _fill(target: etree._Element, text: str, table: _Table) -> None:
    """Set `target` to `text`, its tags the table's elements; a tag that is not one of them, or
    closes none that is open, is text."""
    for child in list(target):
        target.remove(child)
    target.text = None
    stack = [target]
    opened: list[int] = []
    position = 0
    for match in _TOKEN.finditer(text):
        _append(stack[-1], text[position : match.start()])
        position = match.end()
        closing, kind, digits, empty = match.groups()
        number = int(digits)
        found = table.elements[number - 1] if 0 < number <= len(table.elements) else None
        paired = found is not None and _local(found) in _PAIRED
        if found is not None and kind == "x" and empty and not closing and not paired:
            inline = copy.deepcopy(found)
            inline.tail = None
            stack[-1].append(inline)
        elif found is not None and kind == "g" and paired and not (closing or empty):
            stack.append(
                etree.SubElement(
                    stack[-1], found.tag, attrib={str(k): str(v) for k, v in found.attrib.items()}
                )
            )
            opened.append(number)
        elif kind == "g" and closing and not empty and opened and opened[-1] == number:
            stack.pop()
            opened.pop()
        else:
            _append(stack[-1], match.group(0))
    _append(stack[-1], text[position:])


def _append(parent: etree._Element, text: str) -> None:
    if not text:
        return
    if len(parent):
        parent[-1].tail = (parent[-1].tail or "") + text
    else:
        parent.text = (parent.text or "") + text


def _notes(message: _Message) -> Iterator[str]:
    holders = _children(message.unit, "notes") if message.two else [message.unit]
    for holder in holders:
        for note in _children(holder, "note"):
            label = note.get("from") or note.get("category")
            text = "".join(str(part) for part in note.itertext()).strip()
            if text and label not in _SKIPPED_NOTES:
                yield f"{label}: {text}" if label else text


def _messages(root: etree._Element) -> list[_Message]:
    two = _two(root)
    files = _children(root, "file")
    messages = []
    for file in files:
        prefix = f"{file.get('original') or file.get('id')}/" if len(files) > 1 else ""
        for unit in _units(file, two):
            if two:
                segments = _children(unit, "segment")
                for index, segment in enumerate(segments, 1):
                    suffix = f"#{segment.get('id') or index}" if len(segments) > 1 else ""
                    messages.append(_Message(_unit_key(prefix, unit) + suffix, unit, segment, two))
            else:
                messages.append(_Message(_unit_key(prefix, unit), unit, unit, two))
    return messages


def _units(file: etree._Element, two: bool) -> list[etree._Element]:
    """The units of a `<file>` that have an `id` and are to be translated."""
    return [
        unit
        for unit in file.iter("{*}unit" if two else "{*}trans-unit")
        if unit.get("id") and unit.get("translate") != "no"
    ]


def _unit_key(prefix: str, unit: etree._Element) -> str:
    return prefix + (unit.get("id") or "")


def _add_new_units(source: etree._Element, target: etree._Element) -> None:
    """Copy into `target` the units of `source` it has not, without their translation: each
    after the unit before it in `source`, else first in its file."""
    two = _two(source)
    files = _children(source, "file")
    prefixes = [
        f"{file.get('original') or file.get('id')}/" if len(files) > 1 else "" for file in files
    ]
    target_files = _children(target, "file")
    known = {
        _unit_key(prefix, unit): unit
        for prefix, file in zip(prefixes, target_files, strict=False)
        for unit in _units(file, two)
    }
    if not target_files:
        return
    for index, (prefix, file) in enumerate(zip(prefixes, files, strict=True)):
        previous: etree._Element | None = None
        for unit in _units(file, two):
            key = _unit_key(prefix, unit)
            if key in known:
                previous = known[key]
                continue
            added = copy.deepcopy(unit)
            for holder in [added, *_children(added, "segment")]:
                for target_element in _children(holder, "target"):
                    holder.remove(target_element)
                holder.attrib.pop("state", "")
            if previous is not None:
                _insert_after(previous, added)
            else:
                _insert_first(target_files[min(index, len(target_files) - 1)], added)
            known[key] = previous = added


def _insert_first(file: etree._Element, unit: etree._Element) -> None:
    """Put `unit` before a `<file>`'s first unit or group, else last in it."""
    body = _child(file, "body")
    container = body if body is not None else file
    first = next(
        (
            child
            for child in _elements(container)
            if _local(child) in ("unit", "trans-unit", "group")
        ),
        None,
    )
    if first is not None:
        unit.tail = _indent(first)
        first.addprevious(unit)
    elif len(container):
        _insert_after(container[-1], unit)
    else:
        container.append(unit)


def _target(message: _Message) -> etree._Element:
    """The message's `<target>`, added after its `<source>` (or 1.2's `<seg-source>`)."""
    target = message.target
    if target is not None:
        return target
    source = message.source
    assert source is not None
    segmented = _child(message.holder, "seg-source")
    anchor = segmented if segmented is not None else source
    namespace = etree.QName(source).namespace
    target = etree.Element(f"{{{namespace}}}target" if namespace else "target")
    _insert_after(anchor, target)
    return target


def _insert_after(anchor: etree._Element, element: etree._Element) -> None:
    """Put `element` after `anchor`, indented as `anchor` is."""
    element.tail = anchor.tail
    anchor.tail = _indent(anchor)
    anchor.addnext(element)


def _indent(element: etree._Element) -> str | None:
    """The text before `element`: its indentation."""
    previous = element.getprevious()
    if previous is not None:
        return previous.tail
    parent = element.getparent()
    return parent.text if parent is not None else None


def _replace(holder: etree._Element, old: etree._Element | None, new: etree._Element) -> None:
    """Put `new` in place of `old`, or first in `holder`."""
    if old is None:
        new.tail = None
        holder.insert(0, new)
        return
    new.tail = old.tail
    holder.replace(old, new)


def _parse(path: Path) -> tuple[etree._ElementTree, str]:
    """The document in `path`, and its line ending. Raises `ValueError` for one that is not
    XLIFF."""
    text, newline = read_text(path)
    parser = etree.XMLParser(resolve_entities=False, no_network=True)
    try:
        # lxml refuses text with an encoding declaration; the file is read as UTF-8
        root = etree.fromstring(_DECLARATION.sub("", text, count=1), parser)
    except etree.XMLSyntaxError as error:
        raise ValueError(str(error)) from error
    if _local(root) != "xliff":
        raise ValueError(f"its root is <{_local(root)}>, not <xliff>")
    return root.getroottree(), newline


def _serialize(tree: etree._ElementTree, like: Path) -> str:
    """The document, with the XML declaration of `like`, if it has one, in UTF-8."""
    found = _DECLARATION.match(read_text(like)[0])
    declaration = _ENCODING.sub('encoding="UTF-8"', found.group(1)) if found else ""
    body = etree.tostring(tree, encoding="unicode")
    return (f"{declaration}\n" if declaration else "") + body.rstrip("\n") + "\n"


def _two(root: etree._Element) -> bool:
    """Whether the document is XLIFF 2: its version, or its namespace."""
    version = root.get("version") or ""
    return version.startswith("2") or ":xliff:document:2." in (etree.QName(root).namespace or "")


def _local(element: etree._Element) -> str:
    return etree.QName(element).localname


def _elements(parent: etree._Element) -> list[etree._Element]:
    return [child for child in parent if isinstance(child.tag, str)]


def _children(parent: etree._Element, name: str) -> list[etree._Element]:
    return [child for child in _elements(parent) if _local(child) == name]


def _child(parent: etree._Element, name: str) -> etree._Element | None:
    return next(iter(_children(parent, name)), None)
