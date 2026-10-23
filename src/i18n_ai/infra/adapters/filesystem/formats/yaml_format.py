"""Locale YAML, read plain and written round-trip: a target is the source's own document with
its messages translated, so its comments, key order, quoting, block scalars and indent survive.
Read as YAML 1.2, where `no:` (Norwegian) is a key and not `false`."""

import copy
import io
import re
from itertools import pairwise
from pathlib import Path
from typing import Any

from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap, CommentedSeq
from ruamel.yaml.error import YAMLError
from ruamel.yaml.scalarstring import ScalarString

from .....domain.exports.locale import LocaleFormat, SourceFile
from ..files import read_text, write_atomically
from .base import FileFormat

# A key that opens a block: `key:`, nothing after it but a comment.
_OPENER = re.compile(r"^[^\s#-][^#]*:\s*(#.*)?$")


class YamlFormat(FileFormat):
    format = LocaleFormat.YAML
    extensions = (".yml", ".yaml")
    label = "YAML"

    def read(self, path: Path) -> Any:
        text, _ = read_text(path)
        try:
            return _plain(YAML(typ="safe").load(text))
        except YAMLError as error:
            raise ValueError(str(error).replace("\n", " ")) from error

    def write(self, path: Path, content: dict[str, Any], like: SourceFile, key: str | None) -> None:
        text, newline = read_text(like.path)
        yaml = _round_trip(text)
        source = yaml.load(text)
        template = _child(source, like.root_key) if like.root_key is not None else source
        shaped = _overlay(copy.deepcopy(template), content)

        document = shaped
        if key is not None:
            existing = yaml.load(read_text(path)[0]) if path.is_file() else None
            if isinstance(existing, CommentedMap):
                document = existing
            else:
                # A new file, rooted at its locale, opens with the source's comments
                document = CommentedMap()
                if isinstance(source, CommentedMap):
                    document.ca.comment = copy.deepcopy(source.ca.comment)
            _put(document, key, shaped)

        stream = io.StringIO()
        yaml.dump(document, stream)
        write_atomically(path, stream.getvalue(), newline)


def _round_trip(text: str) -> YAML:
    """A round-trip YAML that writes as `text` is written."""
    yaml = YAML()
    yaml.preserve_quotes = True
    yaml.width = 4096  # no folding of long messages
    yaml.explicit_start = text.lstrip().startswith("---")
    mapping, sequence, offset = _indents(text)
    yaml.indent(mapping=mapping, sequence=sequence, offset=offset)
    return yaml


def _indents(text: str) -> tuple[int, int, int]:
    """The indent of a nested mapping, of a sequence's items, and of their dash, from the first
    block of each kind in `text`; ruamel.yaml's defaults otherwise."""
    lines = [
        (len(line) - len(line.lstrip(" ")), line.strip())
        for line in text.splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    mapping: int | None = None
    offset: int | None = None
    for (indent, line), (inner, first) in pairwise(lines):
        if not _OPENER.match(line):
            continue
        if first.startswith("- "):
            offset = inner - indent if offset is None else offset
        elif inner > indent and mapping is None:
            mapping = inner - indent
    mapping = mapping or 2
    offset = max(offset or 0, 0)
    return mapping, offset + 2, offset


def _plain(node: Any) -> Any:
    """`node` as JSON would read it: dicts, lists and the scalars, every key a string."""
    if isinstance(node, dict):
        return {str(key): _plain(value) for key, value in node.items()}
    if isinstance(node, list):
        return [_plain(item) for item in node]
    return node


def _child(node: Any, key: str) -> Any:
    for name, value in node.items():
        if str(name) == key:
            return value
    raise KeyError(key)


def _put(document: CommentedMap, key: str, value: Any) -> None:
    for name in document:
        if str(name) == key:
            document[name] = value
            return
    document[key] = value


def _overlay(node: Any, value: Any) -> Any:
    """`value`, in the place of the source's `node`: what both have keeps the node's comments,
    position and style; a string its quoting or block style."""
    if isinstance(value, dict):
        if not isinstance(node, CommentedMap):
            return value
        names = {str(name): name for name in node}
        for name, original in names.items():
            if name not in value:
                del node[original]
        # The keys left are in `value`'s order; the new ones (plural forms) go in their place
        for index, (name, item) in enumerate(value.items()):
            if name in names:
                node[names[name]] = _overlay(node[names[name]], item)
            else:
                node.insert(index, name, item)
        return node
    if isinstance(value, list):
        if not isinstance(node, CommentedSeq) or len(node) != len(value):
            return value
        for index, item in enumerate(value):
            node[index] = _overlay(node[index], item)
        return node
    if isinstance(value, str) and isinstance(node, ScalarString):
        return type(node)(value)
    if not isinstance(value, str) and type(value) is not bool and value == node:
        return node  # a number as it was written: 0x1F, 1e3
    return value
