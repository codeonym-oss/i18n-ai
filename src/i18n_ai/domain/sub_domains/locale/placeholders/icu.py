"""A small parser of ICU MessageFormat, enough to tell a message's arguments and branches apart
from its text: `Hello {name}`, `{count, number}`, `{count, plural, one {# item} other {# items}}`.

Text is kept as it is written; the caller looks for other placeholders in it."""

from dataclasses import dataclass, field

from ....contract.exceptions.base import DomainException

BRANCHING = frozenset({"plural", "selectordinal", "select"})


class IcuSyntaxError(DomainException):
    """A message whose braces do not make ICU MessageFormat."""

    def __init__(self, reason: str, position: int) -> None:
        super().__init__(message=f"{reason} at character {position}", error_code="ICU_SYNTAX")


@dataclass(frozen=True)
class Text:
    value: str


@dataclass(frozen=True)
class Argument:
    """`{name}`, `{name, type}`, `{name, type, style}`, or a plural, selectordinal or select,
    whose `options` map each selector (`one`, `=0`, `male`) to its message."""

    name: str
    type: str | None = None
    style: str | None = None
    options: dict[str, "Message"] = field(default_factory=dict)

    @property
    def branching(self) -> bool:
        return self.type in BRANCHING


Node = Text | Argument
Message = list[Node]


def parse(text: str, *, quotes: bool) -> Message:
    """Parse `text`. With `quotes`, an apostrophe before `{`, `}` (or `#` in a plural) starts a
    quoted literal, as ICU has it; `''` is an apostrophe either way.

    Raises `IcuSyntaxError`."""
    parser = _Parser(text, quotes)
    message = parser.message(depth=0, in_plural=False)
    if parser.i < len(text):
        raise IcuSyntaxError("unexpected '}'", parser.i)
    return message


def has_braces(text: str) -> bool:
    return "{" in text or "}" in text


class _Parser:
    def __init__(self, text: str, quotes: bool) -> None:
        self.text = text
        self.quotes = quotes
        self.i = 0

    def message(self, depth: int, in_plural: bool) -> Message:
        nodes: Message = []
        buffer: list[str] = []

        def flush() -> None:
            if buffer:
                nodes.append(Text("".join(buffer)))
                buffer.clear()

        text = self.text
        while self.i < len(text):
            char = text[self.i]
            if char == "'" and self.quotes:
                buffer.append(self._apostrophe(in_plural))
                continue
            if char == "{":
                flush()
                nodes.append(self.argument(depth))
                continue
            if char == "}":
                if depth == 0:
                    raise IcuSyntaxError("unexpected '}'", self.i)
                break
            buffer.append(char)
            self.i += 1
        flush()
        return nodes

    def _apostrophe(self, in_plural: bool) -> str:
        """Read an apostrophe at `i`: `''`, a quoted literal, or a plain apostrophe."""
        text = self.text
        following = text[self.i + 1] if self.i + 1 < len(text) else ""
        if following == "'":
            self.i += 2
            return "'"
        if following in "{}" or (following == "#" and in_plural):
            end = self.i + 1
            literal: list[str] = []
            while end < len(text):
                if text[end] == "'":
                    if end + 1 < len(text) and text[end + 1] == "'":
                        literal.append("'")
                        end += 2
                        continue
                    break
                literal.append(text[end])
                end += 1
            self.i = end + 1
            return "".join(literal)
        self.i += 1
        return "'"

    def argument(self, depth: int) -> Argument:
        start = self.i
        self.i += 1
        self._spaces()
        name = self._word(",}")
        if not name:
            raise IcuSyntaxError("an argument without a name", start)
        self._spaces()
        if self._take("}"):
            return Argument(name)
        if not self._take(","):
            raise IcuSyntaxError(f"expected ',' or '}}' after {name!r}", self.i)
        self._spaces()
        kind = self._word(",}")
        if not kind:
            raise IcuSyntaxError(f"an empty type for {name!r}", self.i)
        self._spaces()
        if self._take("}"):
            return Argument(name, kind)
        if not self._take(","):
            raise IcuSyntaxError(f"expected ',' or '}}' after the type of {name!r}", self.i)
        if kind in BRANCHING:
            return Argument(name, kind, options=self._options(name, kind, depth))
        return Argument(name, kind, style=self._style(start))

    def _options(self, name: str, kind: str, depth: int) -> dict[str, Message]:
        options: dict[str, Message] = {}
        while True:
            self._spaces()
            if self.i >= len(self.text):
                raise IcuSyntaxError(f"{name!r} is not closed", self.i)
            if self._take("}"):
                break
            selector = self._word("{}")
            if not selector:
                raise IcuSyntaxError(f"a branch of {name!r} without a selector", self.i)
            if selector.startswith("offset:"):
                continue
            self._spaces()
            if not self._take("{"):
                raise IcuSyntaxError(f"expected '{{' after the selector {selector!r}", self.i)
            options[selector] = self.message(depth + 1, in_plural=kind != "select")
            if not self._take("}"):
                raise IcuSyntaxError(f"the branch {selector!r} of {name!r} is not closed", self.i)
        if "other" not in options:
            raise IcuSyntaxError(f"{name!r} has no 'other' branch", self.i)
        return options

    def _style(self, start: int) -> str:
        level = 0
        begin = self.i
        while self.i < len(self.text):
            char = self.text[self.i]
            if char == "{":
                level += 1
            elif char == "}":
                if level == 0:
                    style = self.text[begin : self.i].strip()
                    self.i += 1
                    return style
                level -= 1
            self.i += 1
        raise IcuSyntaxError("an argument is not closed", start)

    def _spaces(self) -> None:
        while self.i < len(self.text) and self.text[self.i].isspace():
            self.i += 1

    def _word(self, stops: str) -> str:
        begin = self.i
        while (
            self.i < len(self.text)
            and not self.text[self.i].isspace()
            and self.text[self.i] not in stops
        ):
            self.i += 1
        return self.text[begin : self.i]

    def _take(self, char: str) -> bool:
        if self.i < len(self.text) and self.text[self.i] == char:
            self.i += 1
            return True
        return False
