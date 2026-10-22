from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import Any

from ..vo.key_path import KeyPath


@dataclass(frozen=True)
class JsonStyle:
    """How a document's JSON is written, so that a generated locale reads like its source:
    the indent (spaces, a tab, or None for one line) and a newline at the end."""

    indent: int | str | None = 2
    trailing_newline: bool = True


@dataclass(frozen=True)
class LocaleDocument:
    """One locale's messages from one file: a JSON object whose leaves are mostly strings."""

    content: dict[str, Any]
    style: JsonStyle = field(default_factory=JsonStyle)

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
