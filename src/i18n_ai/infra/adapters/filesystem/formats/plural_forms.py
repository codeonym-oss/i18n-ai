"""gettext's `Plural-Forms`, read: its `plural` expression, a C expression of `n`, is evaluated
here rather than trusted, so that a catalog's own numbering of its forms is kept:

    nplurals=3; plural=(n%10==1 && n%100!=11 ? 0
                        : n%10>=2 && n%10<=4 && (n%100<10 || n%100>=20) ? 1 : 2);
"""

import re
from collections import Counter
from collections.abc import Callable

from .....domain.exports.locale import LocaleCode

_HEADER = re.compile(r"nplurals\s*=\s*(\d+)\s*;\s*plural\s*=\s*(.+?);?\s*$", re.DOTALL)
_TOKEN = re.compile(r"\s*(\d+|n|\|\||&&|==|!=|<=|>=|[-+*/%<>!?:()])")
# The counts a numbering is read from: enough for every CLDR rule over integers
_SAMPLES = (*range(1001), 10_000, 100_000, 1_000_000, 2_000_000)

Expression = Callable[[int], int]


def numbering(header: str, locale: LocaleCode) -> tuple[str, ...] | None:
    """The CLDR category of each of the forms `header` numbers, for `locale`: Russian's old
    `nplurals=3` is `('one', 'few', 'many')`. A form no whole count reaches is for a category
    none reaches, in CLDR's order (Lithuanian's `many`, for fractions), else `other`. None when
    the header cannot be read, or its expression leaves its forms."""
    match = _HEADER.search(header)
    if match is None:
        return None
    count = int(match.group(1))
    try:
        plural = _parse(match.group(2))
        hits: list[Counter[str]] = [Counter() for _ in range(count)]
        for n in _SAMPLES:
            index = plural(n)
            if not 0 <= index < count:
                return None
            hits[index][locale.plural_category(n)] += 1
    except (ValueError, ZeroDivisionError, IndexError):
        return None
    reached = {found.most_common(1)[0][0] for found in hits if found}
    unreached = iter([c for c in locale.plural_categories() if c not in reached])
    return tuple(
        found.most_common(1)[0][0] if found else next(unreached, "other") for found in hits
    )


def _parse(text: str) -> Expression:
    tokens = _tokens(text)
    position = 0

    def peek() -> str | None:
        return tokens[position] if position < len(tokens) else None

    def take(expected: str | None = None) -> str:
        nonlocal position
        token = peek()
        if token is None or (expected is not None and token != expected):
            raise ValueError(f"expected {expected or 'more'} in {text!r}")
        position += 1
        return token

    def ternary() -> Expression:
        condition = binary(0)
        if peek() != "?":
            return condition
        take("?")
        then = ternary()
        take(":")
        otherwise = ternary()
        return lambda n: then(n) if condition(n) else otherwise(n)

    def binary(level: int) -> Expression:
        if level == len(_LEVELS):
            return unary()
        left = binary(level + 1)
        while peek() in _LEVELS[level]:
            left = _combine(take(), left, binary(level + 1))
        return left

    def unary() -> Expression:
        token = take()
        if token == "!":
            operand = unary()
            return lambda n: int(not operand(n))
        if token == "(":
            inner = ternary()
            take(")")
            return inner
        if token == "n":
            return lambda n: n
        if token.isdigit():
            value = int(token)
            return lambda n: value
        raise ValueError(f"unexpected {token!r} in {text!r}")

    expression = ternary()
    if peek() is not None:
        raise ValueError(f"unexpected {peek()!r} in {text!r}")
    return expression


_LEVELS = (("||",), ("&&",), ("==", "!="), ("<", "<=", ">", ">="), ("+", "-"), ("*", "/", "%"))

_OPERATORS: dict[str, Callable[[int, int], int]] = {
    "||": lambda a, b: int(bool(a) or bool(b)),
    "&&": lambda a, b: int(bool(a) and bool(b)),
    "==": lambda a, b: int(a == b),
    "!=": lambda a, b: int(a != b),
    "<": lambda a, b: int(a < b),
    "<=": lambda a, b: int(a <= b),
    ">": lambda a, b: int(a > b),
    ">=": lambda a, b: int(a >= b),
    "+": lambda a, b: a + b,
    "-": lambda a, b: a - b,
    "*": lambda a, b: a * b,
    "/": lambda a, b: a // b,
    "%": lambda a, b: a % b,
}


def _combine(operator: str, left: Expression, right: Expression) -> Expression:
    apply = _OPERATORS[operator]
    return lambda n: apply(left(n), right(n))


def _tokens(text: str) -> list[str]:
    tokens = []
    position = 0
    text = text.strip()
    while position < len(text):
        match = _TOKEN.match(text, position)
        if match is None:
            raise ValueError(f"cannot read {text[position:]!r}")
        tokens.append(match.group(1))
        position = match.end()
    return tokens
