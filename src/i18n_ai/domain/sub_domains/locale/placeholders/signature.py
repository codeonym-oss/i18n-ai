from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass

from . import icu
from .tokens import PlaceholderStyle, flat_tokens, mask_braced, styles_in


@dataclass(frozen=True)
class Branching:
    """A plural, selectordinal or select of a message: its selectors, and the placeholders its
    branches use, together; a branch may leave out one the others have."""

    name: str
    kind: str
    selectors: frozenset[str]
    inner: frozenset[str]

    @property
    def is_plural(self) -> bool:
        return self.kind in ("plural", "selectordinal")


@dataclass(frozen=True)
class Signature:
    """What a message must keep through its translation: its placeholders, each as often as it
    appears, and its plurals and selects. Two messages have the same signature when a
    translation of one can stand in for the other in code.

    `error` says why the message's braces are not ICU; its braces then count as placeholders."""

    tokens: tuple[str, ...]
    branchings: tuple[Branching, ...]
    error: str | None = None

    @property
    def empty(self) -> bool:
        return not self.tokens and not self.branchings

    def counts(self) -> Counter[str]:
        return Counter(self.tokens)

    def placeholders(self) -> list[str]:
        """Each placeholder once, in a stable order, for a prompt."""
        names = dict.fromkeys(self.tokens)
        for branching in self.branchings:
            names.update(dict.fromkeys(sorted(branching.inner)))
        return list(names)


def signature_of(text: str, *, quotes: bool) -> Signature:
    """The signature of `text`. `quotes` says whether an apostrophe can quote ICU syntax (see
    `icu.parse`): it can in documents that use ICU."""
    masked, braced = mask_braced(text)
    if not icu.has_braces(masked):
        return Signature(tuple(sorted(flat_tokens(masked, braced))), ())
    try:
        message = icu.parse(masked, quotes=quotes)
    except icu.IcuSyntaxError as error:
        braces = ["{"] * masked.count("{") + ["}"] * masked.count("}")
        return Signature(tuple(sorted(flat_tokens(masked, braced) + braces)), (), error.message)
    tokens: list[str] = []
    branchings: list[Branching] = []
    _collect(message, braced, tokens, branchings)
    ordered = tuple(
        sorted(
            branchings,
            key=lambda branching: (branching.name, branching.kind, sorted(branching.inner)),
        )
    )
    return Signature(tuple(sorted(tokens)), ordered)


def _collect(
    message: icu.Message, braced: list[str], tokens: list[str], branchings: list[Branching]
) -> None:
    for node in message:
        if isinstance(node, icu.Text):
            tokens.extend(flat_tokens(node.value, braced))
        elif node.branching:
            tokens.append(f"{{{node.name}, {node.type}}}")
            inner: list[str] = []
            for branch in node.options.values():
                _collect(branch, braced, inner, branchings)
            branchings.append(
                Branching(node.name, node.type or "", frozenset(node.options), frozenset(inner))
            )
        else:
            parts = [node.name, node.type, node.style]
            tokens.append("{" + ", ".join(part for part in parts if part) + "}")


def detect_styles(texts: Iterable[str]) -> frozenset[PlaceholderStyle]:
    """The families of placeholders a document's messages use."""
    styles: set[PlaceholderStyle] = set()
    for text in texts:
        styles |= styles_in(text)
        masked, _ = mask_braced(text)
        if icu.has_braces(masked):
            try:
                if any(isinstance(node, icu.Argument) for node in icu.parse(masked, quotes=False)):
                    styles.add(PlaceholderStyle.ICU)
            except icu.IcuSyntaxError:
                continue
    return frozenset(styles)


def uses_icu_quotes(texts: Iterable[str]) -> bool:
    """Whether a document is ICU MessageFormat proper, where an apostrophe quotes: one of its
    messages has a typed argument (`{n, number}`) or a plural or select. A document whose only
    arguments are `{name}` may be vue-i18n's, where an apostrophe is only an apostrophe."""
    for text in texts:
        masked, _ = mask_braced(text)
        if not icu.has_braces(masked):
            continue
        try:
            message = icu.parse(masked, quotes=False)
        except icu.IcuSyntaxError:
            continue
        if _typed(message):
            return True
    return False


def _typed(message: icu.Message) -> bool:
    return any(isinstance(node, icu.Argument) and node.type is not None for node in message)
