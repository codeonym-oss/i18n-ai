from dataclasses import dataclass

from ..placeholders import PlaceholderStyle
from ..vo import LocaleFormat, MessageSyntax


@dataclass(frozen=True)
class ConfigHint:
    """A config file that says where a library's locales are: the first file matching `file`, a
    glob from the project's root, read as text and never run, and `pattern`, whose first group
    is the path. The path is relative to the first of the `under` directories it is found in;
    a file's path (Angular's `src/locale/messages.fr.xlf`) gives its directory."""

    file: str
    pattern: str
    under: tuple[str, ...] = ("",)


@dataclass(frozen=True)
class Preset:
    """An i18n library: what reveals it in a project (a dependency in its manifest, or one of
    its files), where its locales are (a config file's word for it, else the usual places), and
    how they are written: their format, the placeholders its messages use, and their syntax,
    which turns on rules of its own in the library's locales."""

    name: str
    library: str
    example: str
    packages: tuple[str, ...] = ()
    files: tuple[str, ...] = ()
    config: tuple[ConfigHint, ...] = ()
    trees: tuple[str, ...] = ()
    format: LocaleFormat | None = None
    placeholders: tuple[PlaceholderStyle, ...] = ()
    syntax: MessageSyntax = MessageSyntax.STANDARD
