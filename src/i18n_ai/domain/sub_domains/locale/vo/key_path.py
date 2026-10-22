import re
from dataclasses import dataclass

Segment = str | int

_PLAIN = re.compile(r"^[A-Za-z0-9_\-$]+$")


@dataclass(frozen=True)
class KeyPath:
    """Where a value sits in a locale document: the keys of its objects and the indexes of its
    arrays, from the top. Shown as `auth.login.title` or `steps[2]`; a key that holds a dot or
    a space is quoted, as in `errors["not.found"]`."""

    segments: tuple[Segment, ...] = ()

    def child(self, segment: Segment) -> "KeyPath":
        return KeyPath((*self.segments, segment))

    def sibling(self, key: str) -> "KeyPath":
        return KeyPath((*self.segments[:-1], key))

    def __str__(self) -> str:
        parts: list[str] = []
        for segment in self.segments:
            if isinstance(segment, int):
                parts.append(f"[{segment}]")
            elif _PLAIN.match(segment):
                parts.append(f".{segment}" if parts else segment)
            else:
                parts.append(f"[{segment!r}]".replace("'", '"'))
        return "".join(parts) or "<root>"
