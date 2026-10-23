from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class PresetView:
    """A preset: its library, what reveals it, where its locales usually are, their format
    (None when the library takes several), and the placeholders its messages use."""

    name: str
    library: str
    example: str
    detected_from: tuple[str, ...]
    format: str | None
    placeholders: tuple[str, ...]


@dataclass(frozen=True)
class PresetMatch:
    """The preset a project uses, and why: `reason` is what revealed it (`react-i18next in
    package.json`), or `chosen` when it was named. `tree` is its locales' directory, which
    `tree_from` names (`l10n.yaml`) or None for the library's usual place; None when it is not
    found."""

    preset: PresetView
    reason: str
    tree: Path | None
    tree_from: str | None
