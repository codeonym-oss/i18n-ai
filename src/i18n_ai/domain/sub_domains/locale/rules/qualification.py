from dataclasses import dataclass

from ..entities.document import LocaleDocument

# Below this share of text among its values, a JSON file is data rather than messages.
TEXT_SHARE = 0.5


@dataclass(frozen=True)
class Qualification:
    """Whether a source file is a locale document worth translating, and why."""

    qualifies: bool
    reason: str
    messages: int = 0


def qualify(document: LocaleDocument | None, error: str | None = None) -> Qualification:
    """Tell a locale document from the other JSON files a locale directory may hold: it is an
    object, and most of its values are text."""
    if document is None:
        return Qualification(False, error or "not a JSON object")
    leaves = [value for _, value in document.leaves()]
    messages = sum(1 for value in leaves if isinstance(value, str) and value.strip())
    if not leaves or messages == 0:
        return Qualification(False, "it holds no text to translate")
    if messages / len(leaves) < TEXT_SHARE:
        return Qualification(
            False, f"only {messages} of its {len(leaves)} values are text: it looks like data"
        )
    return Qualification(True, f"{messages} messages", messages)
