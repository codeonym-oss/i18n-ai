"""The placeholders that are not ICU arguments: what i18n libraries put in a message for code to
fill or render. Each is normalized, so that `{{ name }}` and `{{name}}` are the same placeholder."""

import re
from enum import StrEnum


class PlaceholderStyle(StrEnum):
    """A family of placeholders, as one library or another writes them."""

    DOUBLE_BRACES = "double-braces"  # i18next, vue, angular, handlebars: {{name}}
    ICU = "icu"  # react-intl, next-intl, formatjs, vue-i18n: {name}, {count, plural, ...}
    RAILS = "rails"  # rails, vue-i18n legacy, polyglot: %{name}
    PRINTF = "printf"  # gettext-style: %s, %1$d, %(name)s
    NESTING = "nesting"  # i18next: $t(key)
    LINKED = "linked"  # vue-i18n: @:key, @.lower:key
    TAGS = "tags"  # html and react-i18next's <Trans>: <b>, </b>, <0/>, <br/>


DOUBLE_BRACES = re.compile(r"\{\{-?\s*([^{}]*?)\s*\}\}")
_RAILS = re.compile(r"%\{\s*([^{}\s]+)\s*\}")
_PRINTF = re.compile(
    r"%(?:\d+\$)?(?:\([A-Za-z_][\w.]*\))?[-+#0]*(?:\d+|\*)?(?:\.\d+)?(?:hh|h|ll|l|L|z|j|t)?[sdifuxXoeEgGcp@]"
)
_NESTING = re.compile(r"\$t\([^()]*\)")
_LINKED = re.compile(r"@(?:\.[A-Za-z]+)?:(?:\{[^{}]*\}|[\w.\-]+)")
_TAG = re.compile(r"<\s*(/)?\s*([A-Za-z0-9][\w.\-]*)(?:\s+[^<>]*?)?\s*(/)?\s*>")

_FLAT = (
    (PlaceholderStyle.RAILS, _RAILS),
    (PlaceholderStyle.NESTING, _NESTING),
    (PlaceholderStyle.LINKED, _LINKED),
)

# The placeholders that hold braces, `{{name}}`, `%{name}` and `@:{'key'}`, are swapped for
# private-use characters before ICU parses a message, so that their braces are not taken for
# arguments: U+E000, the index's digits, U+E001.
_BRACED = re.compile(r"\{\{-?\s*[^{}]*?\s*\}\}|%\{\s*[^{}\s]+\s*\}|@(?:\.[A-Za-z]+)?:\{[^{}]*\}")
_SENTINEL = re.compile("\ue000(\\d+)\ue001")


def mask_braced(text: str) -> tuple[str, list[str]]:
    """`text` with each placeholder that holds braces swapped for a sentinel, and the
    normalized placeholders."""
    found: list[str] = []

    def swap(match: re.Match[str]) -> str:
        found.append(re.sub(r"\s+", "", match.group(0)))
        return "\ue000" + str(len(found) - 1) + "\ue001"

    return _BRACED.sub(swap, text), found


def flat_tokens(text: str, braced: list[str]) -> list[str]:
    """The placeholders in a stretch of masked text (see `mask_braced`), each as often as it
    appears."""
    tokens = [braced[int(index)] for index in _SENTINEL.findall(text)]
    text = _SENTINEL.sub(" ", text)
    for _, pattern in _FLAT:
        tokens.extend(re.sub(r"\s+", "", match.group(0)) for match in pattern.finditer(text))
        text = pattern.sub(" ", text)
    for match in _TAG.finditer(text):
        closing, name, self_closing = match.group(1), match.group(2), match.group(3)
        tokens.append(f"</{name}>" if closing else f"<{name}/>" if self_closing else f"<{name}>")
    text = _TAG.sub(" ", text)
    tokens.extend(match.group(0) for match in _PRINTF.finditer(text))
    return tokens


def styles_in(text: str) -> set[PlaceholderStyle]:
    """The families of placeholders `text` uses; ICU is told apart by the caller."""
    styles: set[PlaceholderStyle] = set()
    if DOUBLE_BRACES.search(text):
        styles.add(PlaceholderStyle.DOUBLE_BRACES)
    for style, pattern in _FLAT:
        if pattern.search(text):
            styles.add(style)
    if _TAG.search(text):
        styles.add(PlaceholderStyle.TAGS)
    if _PRINTF.search(DOUBLE_BRACES.sub(" ", text)):
        styles.add(PlaceholderStyle.PRINTF)
    return styles
