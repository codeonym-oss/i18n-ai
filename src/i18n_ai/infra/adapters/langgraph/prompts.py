"""The agents' prompts. The rules they state are the ones `domain.locale.rules` checks: a
message that breaks one comes back with the problem, until it passes or runs out of attempts."""

import json
from collections.abc import Mapping, Sequence
from typing import Any

from ....domain.exports.locale import (
    CARDINAL,
    ORDINAL,
    LocaleCode,
    LocaleSchema,
    PlaceholderStyle,
    SourceUnit,
)

_STYLES = {
    PlaceholderStyle.DOUBLE_BRACES: (
        "`{{name}}` interpolations (keep the inside exactly, e.g. `{{count, number}}`)"
    ),
    PlaceholderStyle.RAILS: "`%{name}` interpolations",
    PlaceholderStyle.PRINTF: "printf conversions such as `%s`, `%d`, `%1$s`, `%(name)s`",
    PlaceholderStyle.NESTING: "`$t(key)` references to other messages",
    PlaceholderStyle.LINKED: "`@:key` and `@.lower:key` linked messages",
    PlaceholderStyle.TAGS: (
        "HTML and component tags such as `<b>`, `</b>`, `<0>`, `<br/>`, with their attributes"
    ),
    PlaceholderStyle.LARAVEL: "`:name` placeholders",
}


def classify_system(source: LocaleCode) -> str:
    return f"""You inspect JSON files found in a website's source locale directory \
({source.display_name}, {source.value}), before they are translated into other languages.

A file qualifies when it holds user-facing messages: interface text, labels, errors, e-mails, \
page copy, in {source.display_name}. It does not qualify when it is configuration, data, a schema, \
a list of codes or identifiers, or anything whose values must not be translated.

Answer whether it qualifies, why in one short sentence, and what part of the website its \
messages are for (e.g. "sign-in and sign-up screens")."""


def classify_human(name: str, sample: str) -> str:
    return f"The file `{name}`, its first values by key path:\n\n```json\n{sample}\n```"


def translate_system(
    schema: LocaleSchema, file: str, subject: str | None, context: str | None
) -> str:
    source, target = schema.source, schema.target
    cardinal = ", ".join(target.plural_categories(CARDINAL))
    ordinal = ", ".join(target.plural_categories(ORDINAL))
    lines = [
        "You are a senior software localizer. You translate the user-interface messages of a "
        f"website from {source.display_name} ({source.value}) into {target.display_name} "
        f"({target.value}).",
    ]
    if context:
        lines.append(f"The website: {context}")
    where = f"The messages come from `{file}`" + (f", for {subject}." if subject else ".")
    lines += [where, "", "Rules. A translation that breaks one is rejected and sent back to you:"]

    rules = [
        f"Translate the meaning the way a native {target.display_name} interface says it, as "
        "concise as the source, with one consistent register. Keep the source's punctuation "
        "role (a label stays a label).",
        "Copy every placeholder character for character: never translate, rename, add or drop one. "
        "Move it to wherever the grammar needs it.",
    ]
    styles = [_STYLES[style] for style in sorted(schema.styles) if style in _STYLES]
    if styles:
        rules.append("This file uses " + "; ".join(styles) + ".")
    if PlaceholderStyle.LARAVEL in schema.styles:
        rules.append(
            "A `:name` renders its value as given, `:Name` capitalized, `:NAME` in capitals: keep "
            "the name, and change its case only where the grammar needs it (at the start of a "
            "sentence)."
        )
    if PlaceholderStyle.TAGS in schema.styles:
        rules.append("Keep every tag and its attributes; translate only the text between tags.")
    if PlaceholderStyle.ICU in schema.styles:
        icu = (
            "ICU MessageFormat: keep each `{name}`, `{name, number}`, `{n, plural, ...}`, "
            "`{x, select, ...}` with its argument names, types, styles and `#`; translate only "
            f"the text inside the branches. In a plural, use exactly the {target.value} "
            f"categories ({cardinal}; for selectordinal: {ordinal}) and keep the explicit "
            "selectors such as `=0`. In a select, keep the same option keywords."
        )
        if schema.quotes:
            icu += " Never write an apostrophe right before `{`: it quotes it. Write ’ instead."
        rules.append(icu)
    if any(unit.plural is not None for unit in schema.units):
        rules.append(
            "A message marked with a `plural` category is that form of a plural, and "
            f"{target.display_name} uses the categories {cardinal} (ordinals: {ordinal}). Write "
            f"the form that category needs in {target.display_name}; show the count with "
            "the source's count placeholder (`{{count}}`, `%{count}`) wherever that form needs it."
        )
    if any(unit.note for unit in schema.units):
        rules.append(
            "A message's `note` is its author's description of it, for translators: use it to "
            "choose the meaning and the tone (a button, a title, a verb or a noun). Never "
            "translate the note itself."
        )
    rules.append(
        "Leave brand and product names, code, URLs, e-mail addresses and keyboard keys as they are."
    )
    if target.direction == "rtl":
        rules.append(
            "The target is written right to left: write it naturally; add no direction marks."
        )
    rules.append("Answer with one translation for each id given, and no other ids.")
    lines += [f"{index}. {rule}" for index, rule in enumerate(rules, start=1)]
    return "\n".join(lines)


def translate_human(
    units: Sequence[SourceUnit], previous: Mapping[str, str], problems: Mapping[str, list[str]]
) -> str:
    messages: list[dict[str, Any]] = []
    for unit in units:
        message: dict[str, Any] = {"id": unit.id, "key": str(unit.path), "text": unit.source}
        if unit.note:
            message["note"] = unit.note
        if unit.plural is not None:
            message["plural"] = unit.plural.category
            if unit.plural.kind == ORDINAL:
                message["ordinal"] = True
        placeholders = unit.signature.placeholders()
        if placeholders:
            message["placeholders"] = placeholders
        if unit.id in previous:
            message["your_previous_translation"] = previous[unit.id]
        if unit.id in problems:
            message["problems_to_fix"] = problems[unit.id]
        messages.append(message)
    intro = "Translate these messages."
    if problems:
        intro = (
            "Your previous translations of these messages were rejected. Fix the problems listed "
            "for each."
        )
    return f"{intro}\n\n```json\n{json.dumps(messages, ensure_ascii=False, indent=1)}\n```"
