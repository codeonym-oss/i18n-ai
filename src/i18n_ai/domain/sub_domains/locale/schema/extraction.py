import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from functools import cached_property
from typing import Any

from ..entities.document import LocaleDocument, is_message
from ..placeholders.signature import Signature, detect_styles, signature_of, uses_icu_quotes
from ..placeholders.tokens import PlaceholderStyle
from ..vo.key_path import KeyPath
from ..vo.locale_code import CARDINAL, ORDINAL, LocaleCode, PluralKind
from ..vo.syntax import MessageSyntax

_ORDER = ("zero", "one", "two", "few", "many", "other")  # CLDR's
_CATEGORIES = frozenset(_ORDER)

# i18next's plural keys: `item_one`, `item_other`, `place_ordinal_two`.
_PLURAL_KEY = re.compile(
    r"^(?P<base>.+?)_(?:(?P<ordinal>ordinal)_)?(?P<category>zero|one|two|few|many|other)$"
)


@dataclass(frozen=True)
class PluralForm:
    """A unit that is one form of a plural: the `category` it is for in the target,
    and the source form it is translated from, the same category or else `other`."""

    kind: PluralKind
    category: str
    source_category: str


@dataclass(frozen=True)
class SourceUnit:
    """One message to translate: its id in the schema, where its translation goes, the source
    text, and the signature the translation must keep; the source file's `note` on it, if any."""

    id: str
    path: KeyPath
    source: str
    signature: Signature
    plural: PluralForm | None = None
    note: str | None = None


@dataclass(frozen=True)
class Slot:
    """Where a unit's translation goes in the template."""

    unit_id: str


class MissingTranslations(Exception):
    def __init__(self, unit_ids: list[str]) -> None:
        super().__init__(f"no translation for the units {', '.join(unit_ids)}")
        self.unit_ids = unit_ids


@dataclass(frozen=True)
class LocaleSchema:
    """The shape a target locale's version of a document must have: the source's keys, in the
    source's order, with its numbers, booleans and empty strings as they are, and a slot for
    each message. A plural family gets the target's plural categories, so `item_one` and
    `item_other` in English become six keys in Arabic and one in Japanese; so does a nested one,
    Rails' `item: {one: ..., other: ...}`.

    `quotes` says the document is ICU MessageFormat, where an apostrophe can quote; `syntax` is
    its tree's."""

    source: LocaleCode
    target: LocaleCode
    units: tuple[SourceUnit, ...]
    template: dict[str, Any]
    styles: frozenset[PlaceholderStyle]
    quotes: bool
    syntax: MessageSyntax = MessageSyntax.STANDARD

    def unit(self, unit_id: str) -> SourceUnit:
        return self._by_id[unit_id]

    @cached_property
    def _by_id(self) -> dict[str, SourceUnit]:
        return {unit.id: unit for unit in self.units}

    def render(self, translations: Mapping[str, str]) -> dict[str, Any]:
        """The target document. Raises `MissingTranslations` unless every unit has one."""
        missing = [unit.id for unit in self.units if unit.id not in translations]
        if missing:
            raise MissingTranslations(missing)
        rendered: dict[str, Any] = _render(self.template, translations)
        return rendered


def extract_schema(
    document: LocaleDocument,
    source: LocaleCode,
    target: LocaleCode,
    syntax: MessageSyntax = MessageSyntax.STANDARD,
) -> LocaleSchema:
    """The schema of `document`'s translation from `source` into `target`, in its tree's
    `syntax`."""
    texts = list(document.strings())
    builder = _Builder(target, uses_icu_quotes(texts), syntax, document.notes)
    template = builder.object(document.content, KeyPath())
    return LocaleSchema(
        source=source,
        target=target,
        units=tuple(builder.units),
        template=template,
        styles=detect_styles(texts, syntax),
        quotes=builder.quotes,
        syntax=syntax,
    )


class _Builder:
    def __init__(
        self,
        target: LocaleCode,
        quotes: bool,
        syntax: MessageSyntax,
        notes: Mapping[KeyPath, str],
    ) -> None:
        self.target = target
        self.quotes = quotes
        self.syntax = syntax
        self.notes = notes
        self.units: list[SourceUnit] = []

    def node(self, value: Any, path: KeyPath) -> Any:
        if isinstance(value, dict):
            if _is_nested_family(value):
                # Rails keeps a `zero` the language has not: it is what a count of 0 shows
                keep = ("zero",) if "zero" in value else ()
                return self.family(value, CARDINAL, path, str, keep, note=self.notes.get(path))
            return self.object(value, path)
        if isinstance(value, list):
            return [self.node(item, path.child(index)) for index, item in enumerate(value)]
        if is_message(value):
            return self.slot(path, value, None, self.notes.get(path))
        return value

    def object(self, node: dict[str, Any], path: KeyPath) -> dict[str, Any]:
        families = _families(node)
        member_of = {key: family for family, forms in families.items() for key in forms.values()}
        rendered: dict[str, Any] = {}
        done: set[tuple[str, PluralKind]] = set()
        for key, value in node.items():
            family = member_of.get(key)
            if family is None:
                rendered[key] = self.node(value, path.child(key))
                continue
            if family in done:
                continue
            # A family is laid out where its first form was, with the target's categories
            done.add(family)
            base, kind = family
            forms = {category: node[key] for category, key in families[family].items()}
            prefix = f"{base}_ordinal_" if kind == ORDINAL else f"{base}_"
            rendered |= self.family(forms, kind, path, prefix.__add__)
        return rendered

    def family(
        self,
        forms: dict[str, Any],
        kind: PluralKind,
        path: KeyPath,
        key_of: Callable[[str], str],
        keep: tuple[str, ...] = (),
        note: str | None = None,
    ) -> dict[str, Any]:
        """A plural family's forms, by category, under the target's categories (and `keep`),
        each translated from the source's own form or else from `other`, with that form's note
        or else the family's."""
        wanted = set(self.target.plural_categories(kind)) | set(keep)
        rendered: dict[str, Any] = {}
        for category in (category for category in _ORDER if category in wanted):
            source_category = category if category in forms else "other"
            text = forms[source_category]
            key = key_of(category)
            form = PluralForm(kind, category, source_category)
            source = path.child(key_of(source_category))
            rendered[key] = (
                self.slot(path.child(key), text, form, self.notes.get(source, note))
                if is_message(text)
                else text
            )
        return rendered

    def slot(self, path: KeyPath, text: str, plural: PluralForm | None, note: str | None) -> Slot:
        unit = SourceUnit(
            id=str(len(self.units) + 1),
            path=path,
            source=text,
            signature=signature_of(text, quotes=self.quotes, syntax=self.syntax),
            plural=plural,
            note=note,
        )
        self.units.append(unit)
        return Slot(unit.id)


def _families(node: dict[str, Any]) -> dict[tuple[str, PluralKind], dict[str, str]]:
    """The plural families among an object's keys: two forms or more of one base, `other`
    among them, each a string."""
    families: dict[tuple[str, PluralKind], dict[str, str]] = {}
    for key, value in node.items():
        match = _PLURAL_KEY.match(key)
        if match is None or not isinstance(value, str):
            continue
        kind = ORDINAL if match.group("ordinal") else CARDINAL
        families.setdefault((match.group("base"), kind), {})[match.group("category")] = key
    return {
        family: forms for family, forms in families.items() if "other" in forms and len(forms) >= 2
    }


def _is_nested_family(node: dict[str, Any]) -> bool:
    """A plural family as its own object: two forms or more, `other` among them, each a string,
    and nothing else."""
    return (
        len(node) >= 2
        and "other" in node
        and all(key in _CATEGORIES and isinstance(value, str) for key, value in node.items())
    )


def _render(node: Any, translations: Mapping[str, str]) -> Any:
    if isinstance(node, Slot):
        return translations[node.unit_id]
    if isinstance(node, dict):
        return {key: _render(value, translations) for key, value in node.items()}
    if isinstance(node, list):
        return [_render(item, translations) for item in node]
    return node
