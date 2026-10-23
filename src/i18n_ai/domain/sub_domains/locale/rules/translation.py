"""The rules a translated message must follow before it is written: it says something, it keeps
every placeholder of its source, and its plurals and selects still work in code."""

import re
from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum

from ..entities.document import LocaleDocument
from ..placeholders.signature import Branching, signature_of
from ..schema.extraction import LocaleSchema, SourceUnit
from ..vo.key_path import KeyPath
from ..vo.locale_code import CARDINAL, ORDINAL


class Severity(StrEnum):
    ERROR = "error"  # the translation is refused
    WARNING = "warning"  # the translation is kept, and the warning reported


class ViolationCode(StrEnum):
    MISSING = "missing"
    EMPTY = "empty"
    PLACEHOLDERS = "placeholders"
    ICU_SYNTAX = "icu-syntax"
    SELECT_OPTIONS = "select-options"
    PLURAL_SELECTORS = "plural-selectors"
    BRANCH_PLACEHOLDERS = "branch-placeholders"
    PLURAL_CATEGORIES = "plural-categories"
    UNCHANGED = "unchanged"


@dataclass(frozen=True)
class Violation:
    unit_id: str
    path: KeyPath
    code: ViolationCode
    message: str
    severity: Severity = Severity.ERROR


_WORD = re.compile(r"[^\W\d_]{3,}")
# The count placeholder: i18next's {{count}}, {{count, number}}, Rails' %{count}
_COUNT = re.compile(r"^(?:\{\{?count(?:,[^}]*)?\}\}?|%\{count\})$")


def normalize(unit: SourceUnit, text: str) -> str:
    """`text` with its source's leading and trailing whitespace, which code often relies on."""
    source = unit.source
    lead = source[: len(source) - len(source.lstrip())]
    trail = source[len(source.rstrip()) :]
    return lead + text.strip() + trail


def check(schema: LocaleSchema, unit: SourceUnit, text: str | None) -> list[Violation]:
    """What is wrong with `text` as `unit`'s translation; errors first. None is a missing one."""

    def violation(
        code: ViolationCode, message: str, severity: Severity = Severity.ERROR
    ) -> Violation:
        return Violation(unit.id, unit.path, code, message, severity)

    if text is None:
        return [violation(ViolationCode.MISSING, "no translation was given")]
    if not text.strip():
        return [violation(ViolationCode.EMPTY, "the translation is empty")]

    source = unit.signature
    translated = signature_of(text, quotes=schema.quotes)
    if source.error is None and translated.error is not None:
        return [
            violation(ViolationCode.ICU_SYNTAX, f"the ICU braces are broken: {translated.error}")
        ]

    found: list[Violation] = []
    # 1. Every placeholder, as often as in the source
    missing = source.counts() - translated.counts()
    extra = translated.counts() - source.counts()
    if unit.plural is not None:
        # A plural form may show the count or not: Russian's `one` is also 21, English's is not
        missing = Counter({token: n for token, n in missing.items() if not _COUNT.match(token)})
        extra = Counter({token: n for token, n in extra.items() if not _COUNT.match(token)})
    if missing or extra:
        parts = []
        if missing:
            parts.append("missing " + _listed(missing))
        if extra:
            parts.append("unexpected " + _listed(extra))
        hint = ""
        if schema.quotes and "'{" in text:
            hint = " (in ICU an apostrophe before '{' quotes it: write ’ or '' instead)"
        found.append(violation(ViolationCode.PLACEHOLDERS, "; ".join(parts) + hint))

    # 2. The plurals and selects, matched by argument name
    for theirs, ours in _pairs(source.branchings, translated.branchings):
        if ours is None:
            continue
        found.extend(_branching(schema, unit, theirs, ours))

    # 3. A message left as it was (a brand, or forgotten)
    changes_language = schema.source.language != schema.target.language
    if (
        changes_language
        and text.strip() == unit.source.strip()
        and _WORD.search(_text_only(unit.source))
    ):
        found.append(violation(ViolationCode.UNCHANGED, "left as in the source", Severity.WARNING))

    return sorted(found, key=lambda item: item.severity != Severity.ERROR)


def _branching(
    schema: LocaleSchema, unit: SourceUnit, source: Branching, translated: Branching
) -> list[Violation]:
    found: list[Violation] = []
    name = f"{{{source.name}, {source.kind}}}"
    if not source.is_plural:
        if translated.selectors != source.selectors:
            options = ", ".join(sorted(source.selectors))
            message = f"{name} must keep exactly the options {options}"
            found.append(Violation(unit.id, unit.path, ViolationCode.SELECT_OPTIONS, message))
    else:
        kind = ORDINAL if source.kind == "selectordinal" else CARDINAL
        categories = schema.target.plural_categories(kind)
        explicit = {selector for selector in source.selectors if selector.startswith("=")}
        if explicit - translated.selectors:
            message = f"{name} must keep the exact selectors {', '.join(sorted(explicit))}"
            found.append(Violation(unit.id, unit.path, ViolationCode.PLURAL_SELECTORS, message))
        named = {selector for selector in translated.selectors if not selector.startswith("=")}
        if named != set(categories):
            message = (
                f"{name} should have the {schema.target.value} categories {', '.join(categories)}"
            )
            found.append(
                Violation(
                    unit.id, unit.path, ViolationCode.PLURAL_CATEGORIES, message, Severity.WARNING
                )
            )
    if translated.inner != source.inner:
        lost = ", ".join(sorted(source.inner - translated.inner)) or "none"
        added = ", ".join(sorted(translated.inner - source.inner)) or "none"
        message = (
            f"the branches of {name} must use the same placeholders "
            f"(missing: {lost}; unexpected: {added})"
        )
        found.append(Violation(unit.id, unit.path, ViolationCode.BRANCH_PLACEHOLDERS, message))
    return found


def _pairs(
    source: tuple[Branching, ...], translated: tuple[Branching, ...]
) -> list[tuple[Branching, Branching | None]]:
    remaining = list(translated)
    pairs: list[tuple[Branching, Branching | None]] = []
    for branching in source:
        match = next(
            (b for b in remaining if (b.name, b.kind) == (branching.name, branching.kind)), None
        )
        if match is not None:
            remaining.remove(match)
        pairs.append((branching, match))
    return pairs


def _listed(tokens: Counter[str]) -> str:
    return ", ".join(
        token if count == 1 else f"{token} ×{count}" for token, count in sorted(tokens.items())
    )


def _text_only(text: str) -> str:
    return re.sub(r"\{[^{}]*\}|<[^<>]*>|%\S", " ", text)


def errors(violations: list[Violation]) -> list[Violation]:
    return [violation for violation in violations if violation.severity == Severity.ERROR]


def reusable_translations(schema: LocaleSchema, existing: LocaleDocument | None) -> dict[str, str]:
    """The units an existing target document already translates well: a message at the unit's
    path that passes `check`. Only the others need translating."""
    if existing is None:
        return {}
    reused: dict[str, str] = {}
    for unit in schema.units:
        value = existing.get(unit.path)
        if isinstance(value, str) and value.strip() and not errors(check(schema, unit, value)):
            reused[unit.id] = value
    return reused


def fallback(schema: LocaleSchema, failed: Mapping[str, list[Violation]]) -> dict[str, str]:
    """The source text of each failed unit, which keeps the target document whole."""
    return {unit_id: schema.unit(unit_id).source for unit_id in failed}
