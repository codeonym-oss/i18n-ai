"""Laravel's pipe plurals, as `trans_choice` reads them: `one apple|many apples`, or with ranges,
`{0} none|[1,19] some|[20,*] many`. A form with a range is chosen by its range; the others by
the language's plural index, from Laravel's own table, which is not CLDR's (French has 2 forms).

The table is Laravel's `MessageSelector::getPluralIndex` (MIT), whose rules are derived from code
of the Zend Framework (2010-09-25), subject to the new BSD license
(https://framework.zend.com/license), Copyright (c) 2005-2010 Zend Technologies USA Inc. Every
region the table lists takes its language's rule, so it is kept by language. Laravel itself looks
up the locale as spelled, and gives one form to a region it does not list (`sr_Latn`): here it
gets its language's forms, of which Laravel would show the first."""

import re
from collections.abc import Callable
from dataclasses import dataclass

from ..vo.locale_code import LocaleCode

# A form's range, at its very start as Laravel reads it: `{0}`, `[1,19]`, `[20,*]`
_RANGE = re.compile(r"^[{\[][-?\d*,.]*[}\]]")


@dataclass(frozen=True)
class PipePlural:
    """A pipe plural's forms: each one's range as written, or None, and its text after it."""

    ranges: tuple[str | None, ...]
    forms: tuple[str, ...]


def parse_pipes(text: str) -> PipePlural | None:
    """The pipe plural `text` is: one with a range, or a pipe with no space on either side of
    it. None for text, as `Dashboard | Acme`, which only `trans_choice` would split."""
    if "|" not in text:
        return None
    shape = split_pipes(text)
    spaced = all(
        text[index - 1 : index] == " " and text[index + 1 : index + 2] == " "
        for index, char in enumerate(text)
        if char == "|"
    )
    return None if spaced and not any(shape.ranges) else shape


def split_pipes(text: str) -> PipePlural:
    """`text` split at each pipe, as `trans_choice` splits it, whatever it is."""
    segments = text.split("|")
    ranges = tuple(match.group(0) if (match := _RANGE.match(part)) else None for part in segments)
    forms = tuple(part[len(found or "") :] for part, found in zip(segments, ranges, strict=True))
    return PipePlural(ranges, forms)


_Rule = Callable[[int], int]

_RULES: tuple[tuple[tuple[str, ...], _Rule], ...] = (
    (
        ("az", "bo", "dz", "id", "ja", "jv", "ka", "km", "kn", "ko", "ms", "th", "tr", "vi", "zh"),
        lambda n: 0,
    ),
    (
        (
            "af", "bg", "bn", "ca", "da", "de", "el", "en", "eo", "es", "et", "eu", "fa", "fi",
            "fo", "fur", "fy", "gl", "gu", "ha", "he", "hu", "is", "it", "ku", "lb", "ml", "mn",
            "mr", "nah", "nb", "ne", "nl", "nn", "no", "om", "or", "pa", "pap", "ps", "pt", "so",
            "sq", "sv", "sw", "ta", "te", "tk", "ur", "zu",
        ),
        lambda n: 0 if n == 1 else 1,
    ),
    (
        ("am", "bh", "fil", "fr", "gun", "hi", "hy", "ln", "mg", "nso", "ti", "wa", "xbr"),
        lambda n: 0 if n in (0, 1) else 1,
    ),
    (
        ("be", "bs", "hr", "ru", "sr", "uk"),
        lambda n: (
            0 if n % 10 == 1 and n % 100 != 11
            else 1 if 2 <= n % 10 <= 4 and (n % 100 < 10 or n % 100 >= 20)
            else 2
        ),
    ),
    (("cs", "sk"), lambda n: 0 if n == 1 else 1 if 2 <= n <= 4 else 2),
    (("ga",), lambda n: 0 if n == 1 else 1 if n == 2 else 2),
    (
        ("lt",),
        lambda n: (
            0 if n % 10 == 1 and n % 100 != 11
            else 1 if n % 10 >= 2 and (n % 100 < 10 or n % 100 >= 20)
            else 2
        ),
    ),
    (
        ("sl",),
        lambda n: 0 if n % 100 == 1 else 1 if n % 100 == 2 else 2 if n % 100 in (3, 4) else 3,
    ),
    (("mk",), lambda n: 0 if n % 10 == 1 else 1),
    (
        ("mt",),
        lambda n: (
            0 if n == 1
            else 1 if n == 0 or 1 < n % 100 < 11
            else 2 if 10 < n % 100 < 20
            else 3
        ),
    ),
    (("lv",), lambda n: 0 if n == 0 else 1 if n % 10 == 1 and n % 100 != 11 else 2),
    (
        ("pl",),
        lambda n: (
            0 if n == 1 else 1 if 2 <= n % 10 <= 4 and (n % 100 < 12 or n % 100 > 14) else 2
        ),
    ),
    (("cy",), lambda n: 0 if n == 1 else 1 if n == 2 else 2 if n in (8, 11) else 3),
    (("ro",), lambda n: 0 if n == 1 else 1 if n == 0 or 0 < n % 100 < 20 else 2),
    (
        ("ar",),
        lambda n: (
            0 if n == 0
            else 1 if n == 1
            else 2 if n == 2
            else 3 if 3 <= n % 100 <= 10
            else 4 if 11 <= n % 100 <= 99
            else 5
        ),
    ),
)  # fmt: skip
_BY_LANGUAGE = {language: rule for languages, rule in _RULES for language in languages}
# The counts a form is told by: enough to reach every form of every rule
_SAMPLES = range(201)
_SHOWN = 6


def laravel_forms(locale: LocaleCode) -> tuple[str, ...]:
    """The forms Laravel gives `locale`'s pipe plurals, each told by the counts it is chosen
    for: `("0, 1", "2, 3, 4, 5, 6, 7, …")` for French. A language Laravel does not know has one
    form, as Laravel then always takes the first."""
    rule = _BY_LANGUAGE.get(locale.language)
    if rule is None:
        return ("every count",)
    counts: dict[int, list[int]] = {}
    for n in _SAMPLES:
        counts.setdefault(rule(n), []).append(n)
    if len(counts) == 1:
        return ("every count",)
    return tuple(_told(counts[index]) for index in sorted(counts))


def _told(counts: list[int]) -> str:
    shown = ", ".join(str(n) for n in counts[:_SHOWN])
    return shown + ", …" if len(counts) > _SHOWN else shown
