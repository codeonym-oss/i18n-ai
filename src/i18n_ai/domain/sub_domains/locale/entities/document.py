import re
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any

from ..vo.key_path import KeyPath

# A Ruby symbol, as Rails' `date.order` lists them (`:year`): a name, not text.
_SYMBOL = re.compile(r"^:[A-Za-z_]\w*$")


def is_message(value: Any) -> bool:
    """Whether a leaf is text to translate: a string with something in it, and not a Ruby
    symbol."""
    return isinstance(value, str) and bool(value.strip()) and not _SYMBOL.match(value)


@dataclass(frozen=True)
class LocaleDocument:
    """One locale's messages from one file: an object, read from JSON or YAML, whose leaves are
    mostly strings. How the file is written is the file's own business."""

    content: dict[str, Any]

    def leaves(self) -> Iterator[tuple[KeyPath, Any]]:
        """Every leaf, with its path, in document order."""
        yield from _leaves(self.content, KeyPath())

    def strings(self) -> Iterator[str]:
        for _, value in self.leaves():
            if isinstance(value, str):
                yield value

    def get(self, path: KeyPath) -> Any:
        """The value at `path`, or None."""
        node: Any = self.content
        for segment in path.segments:
            if isinstance(node, list) and isinstance(segment, int) and 0 <= segment < len(node):
                node = node[segment]
                continue
            if isinstance(node, dict) and isinstance(segment, str) and segment in node:
                node = node[segment]
                continue
            return None
        return node


def _leaves(node: Any, path: KeyPath) -> Iterator[tuple[KeyPath, Any]]:
    if isinstance(node, dict):
        for key, value in node.items():
            yield from _leaves(value, path.child(key))
    elif isinstance(node, list):
        for index, value in enumerate(node):
            yield from _leaves(value, path.child(index))
    else:
        yield path, node
