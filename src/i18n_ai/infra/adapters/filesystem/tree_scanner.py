"""Finding a locale tree from the path a user gives:

- a locale directory, `locales/en`: the directory layout, its siblings the other locales;
- a locale file, `messages/en.json`: the file layout, its siblings the other locales; their
  names may share a prefix, as Flutter's `app_en.arb` and `app_fr.arb`;
- a bundle, `i18n.json` holding `{"en": {...}, "fr": {...}}`: the bundle layout;
- the directory holding the locales, `locales/`: whichever of the first two it holds, with the
  source named, or `en` when there is one, or the only locale.

Its files are in one of the `formats`, the one asked or the only one there. A file whose only
key is its locale, as Rails writes `en.yml`, holds its messages under that key.

`detect` looks for those trees under a project, for the user to pick one."""

import fnmatch
import re
from collections import deque
from collections.abc import Iterable
from pathlib import Path, PurePosixPath

from ....application.ports.locale import ILocaleTreeScanner, TreeCandidate, TreeRequest
from ....domain.exports.locale import (
    InvalidLocaleCode,
    LocaleCode,
    LocaleDocument,
    LocaleFormat,
    LocaleTree,
    LocaleTreeNotFound,
    MixedLocaleFormats,
    SourceFile,
    SourceLocaleUnknown,
    TreeLayout,
)
from .formats import FileFormat, extensions, format_of, load_document

_SKIPPED = {"node_modules", "__pycache__", "dist", "build"}
# Where a locale file's name prefix ends: `app_`, `messages-`, `strings.`
_PREFIX_END = re.compile(r"[_.-]")
_DEFAULT_SOURCE = LocaleCode("en")

# How far `detect` looks: the directories below the project's, and how many at most.
_DETECT_DEPTH = 5
_DETECT_DIRECTORIES = 5000
_DETECT_SKIPPED = _SKIPPED | {"vendor", "venv", "target", "coverage", "out", "site-packages"}
# A bundle is read whole to know it is one: bigger files are not locales.
_BUNDLE_BYTES = 2_000_000
# CLDR knows many three-letter languages that are also directory names (`src`, `lib`...): only
# these few are taken for locales when detecting.
_DETECTED_THREE_LETTERS = {"ast", "chr", "ckb", "fil", "gsw", "haw", "kab", "yue"}
# A lone locale is taken for a tree only in a directory named like one, or when it is English.
_TREE_NAMES = {
    "i18n", "intl", "l10n", "lang", "langs", "language", "languages", "locale", "locales",
    "messages", "translations", "translation",
}  # fmt: skip


class FileSystemLocaleTreeScanner(ILocaleTreeScanner):
    async def scan(self, request: TreeRequest) -> LocaleTree:
        path = request.path.expanduser().resolve()
        if not path.exists():
            raise LocaleTreeNotFound(str(path), "it does not exist")
        if path.is_file():
            return self._from_file(path, request)
        return self._from_directory(path, request)

    async def detect(self, root: Path) -> list[TreeCandidate]:
        return self._detect(root)

    def _detect(self, root: Path) -> list[TreeCandidate]:
        """Breadth first, so the shallowest trees come first; a tree's directories are not
        looked into."""
        queue = deque([(root.expanduser().resolve(), 0)])
        found: list[TreeCandidate] = []
        visited = 0
        while queue and visited < _DETECT_DIRECTORIES:
            directory, depth = queue.popleft()
            visited += 1
            try:
                children = sorted(directory.iterdir())
            except OSError:
                continue
            tree = _tree_in(directory, children)
            found.extend(_bundles_in(children))
            if tree is not None:
                found.append(tree)
                continue
            if depth < _DETECT_DEPTH:
                queue.extend(
                    (child, depth + 1)
                    for child in children
                    if child.is_dir()
                    and not child.name.startswith(".")
                    and child.name not in _DETECT_SKIPPED
                )
        return found

    # The path is a file: a locale file, or a bundle

    def _from_file(self, path: Path, request: TreeRequest) -> LocaleTree:
        adapter = format_of(path)
        if adapter is None or (request.format is not None and adapter.format != request.format):
            wanted = ", ".join(extensions(request.format))
            raise LocaleTreeNotFound(str(path), f"it is not a locale file ({wanted})")
        named = _named(path.stem, request.source)
        if named is not None:
            return self._file_layout(path.parent, path, named[1], request)

        try:
            content = adapter.read(path)
        except (OSError, ValueError) as error:
            raise LocaleTreeNotFound(
                str(path), f"it is not valid {adapter.label} ({error})"
            ) from error
        locales = _bundle_locales(content)
        if not locales:
            raise LocaleTreeNotFound(
                str(path), "its name is not a locale code, and its keys are not locales"
            )
        source = _choose_source(str(path), locales, request.source)
        document = LocaleDocument(content[source.value])
        return LocaleTree(
            root=path,
            layout=TreeLayout.BUNDLE,
            source=source,
            files=(SourceFile(PurePosixPath(path.name), path, document, root_key=source.value),),
            existing=tuple(locale for locale in locales if not locale.same_as(source)),
            output=_output(request, path),
            format=adapter.format,
        )

    def _file_layout(
        self, root: Path, path: Path, source: LocaleCode, request: TreeRequest
    ) -> LocaleTree:
        adapter = format_of(path)
        assert adapter is not None
        prefix = _prefix(path.stem, source)
        siblings = [file for file in root.glob(f"{prefix}*{path.suffix}") if file.is_file()]
        existing = _locales(file.stem.removeprefix(prefix) for file in siblings if file != path)
        return LocaleTree(
            root=root,
            layout=TreeLayout.FILE,
            source=source,
            files=(_source_file(PurePosixPath(path.name), path, adapter, source),),
            existing=existing,
            output=_output(request, root),
            format=adapter.format,
            prefix=prefix,
        )

    # The path is a directory: a locale's, or the one holding the locales

    def _from_directory(self, path: Path, request: TreeRequest) -> LocaleTree:
        locale = _locale_of(path.name, request.source)
        if locale is not None:
            return self._directory_layout(path.parent, path, locale, request)

        directories = {child.name: child for child in path.iterdir() if child.is_dir()}
        locale_directories = _locales(directories)
        if locale_directories:
            source = _choose_source(str(path), locale_directories, request.source)
            return self._directory_layout(path, directories[source.value], source, request)

        by_locale: dict[str, Path] = {}
        for child in sorted(path.iterdir()):
            if child.suffix.lower() not in extensions(request.format) or not child.is_file():
                continue
            named = _named(child.stem, None)
            if named is not None:
                by_locale.setdefault(named[1].value, child)  # unprefixed first: `en` < `app_en`
        _one_format(path, list(by_locale.values()))
        locale_files = _locales(by_locale)
        if locale_files:
            source = _choose_source(str(path), locale_files, request.source)
            return self._file_layout(path, by_locale[source.value], source, request)

        raise LocaleTreeNotFound(
            str(path), "it holds no locale directory (en/) and no locale file (en.json, en.yml)"
        )

    def _directory_layout(
        self, root: Path, directory: Path, source: LocaleCode, request: TreeRequest
    ) -> LocaleTree:
        paths: list[Path] = []
        names: list[PurePosixPath] = []
        wanted = extensions(request.format)
        for path in sorted(directory.rglob("*")):
            relative = path.relative_to(directory)
            if path.suffix.lower() not in wanted or not path.is_file():
                continue
            if any(part.startswith(".") or part in _SKIPPED for part in relative.parts[:-1]):
                continue
            name = PurePosixPath(relative.as_posix())
            if _selected(str(name), request.include, request.exclude):
                paths.append(path)
                names.append(name)
        found = _one_format(directory, paths)
        files = []
        for name, path in zip(names, paths, strict=True):
            adapter = format_of(path)
            assert adapter is not None
            files.append(_source_file(name, path, adapter, source))
        siblings = (child.name for child in root.iterdir() if child.is_dir() and child != directory)
        return LocaleTree(
            root=root,
            layout=TreeLayout.DIRECTORY,
            source=source,
            files=tuple(files),
            existing=_locales(siblings),
            output=_output(request, root),
            format=found or request.format or LocaleFormat.JSON,
        )


def _source_file(
    name: PurePosixPath, path: Path, adapter: FileFormat, source: LocaleCode
) -> SourceFile:
    """A source file, its messages under its locale's key when that is its only key."""
    document, error = load_document(path, adapter)
    if document is not None and len(document.content) == 1:
        [(key, content)] = document.content.items()
        locale = LocaleCode.recognized(key)
        if isinstance(content, dict) and locale is not None and locale.same_as(source):
            return SourceFile(name, path, LocaleDocument(content), root_key=key)
    return SourceFile(name, path, document, error)


def _one_format(path: Path, files: list[Path]) -> LocaleFormat | None:
    """The format of `files`, or None for no file. Raises `MixedLocaleFormats` for several."""
    formats = sorted({adapter.format for file in files if (adapter := format_of(file))})
    if len(formats) > 1:
        raise MixedLocaleFormats(str(path), [format.value for format in formats])
    return formats[0] if formats else None


def _tree_in(directory: Path, children: list[Path]) -> TreeCandidate | None:
    """The tree `directory` holds: locale directories with locale files in them, or locale
    files."""
    formats: dict[str, set[LocaleFormat]] = {}
    for child in children:
        if child.is_dir():
            # The first file tells the format; `scan` finds out whether they all share it
            first = next((file for file in child.rglob("*") if format_of(file) is not None), None)
            if first is not None:
                formats[child.name] = {format_of(first).format}  # type: ignore[union-attr]
    locale_directories = _detected(directory, formats)
    if locale_directories:
        return TreeCandidate(
            directory,
            TreeLayout.DIRECTORY,
            locale_directories,
            _formats(formats[locale.value] for locale in locale_directories),
        )
    files = {
        named[1].value: {adapter.format}
        for child in children
        if (adapter := format_of(child)) is not None
        and child.is_file()
        and (named := _named(child.stem, None)) is not None
    }
    locale_files = _detected(directory, files)
    if locale_files:
        return TreeCandidate(
            directory,
            TreeLayout.FILE,
            locale_files,
            _formats(files[locale.value] for locale in locale_files),
        )
    return None


def _formats(found: Iterable[set[LocaleFormat]]) -> tuple[LocaleFormat, ...]:
    return tuple(sorted(set().union(*found)))


def _detected(directory: Path, names: Iterable[str]) -> tuple[LocaleCode, ...]:
    """The locales among `names` that are likely one, not a directory named like one."""
    locales = tuple(
        locale
        for locale in _locales(names)
        if len(locale.language) == 2 or locale.language in _DETECTED_THREE_LETTERS
    )
    if len(locales) == 1 and directory.name.lower() not in _TREE_NAMES:
        return locales if locales[0].language == "en" else ()
    return locales


def _bundles_in(children: list[Path]) -> list[TreeCandidate]:
    bundles = []
    for child in children:
        adapter = format_of(child)
        if adapter is None or _named(child.stem, None) is not None:
            continue
        try:
            if not child.is_file() or child.stat().st_size > _BUNDLE_BYTES:
                continue
            content = adapter.read(child)
        except (OSError, ValueError):
            continue
        locales = _bundle_locales(content)
        if locales:
            bundles.append(TreeCandidate(child, TreeLayout.BUNDLE, locales, (adapter.format,)))
    return bundles


def _locale_of(name: str, source: LocaleCode | None) -> LocaleCode | None:
    """The locale `name` spells, if it is a locale code; the source, too, though CLDR may not
    know it."""
    try:
        locale = LocaleCode(name)
    except InvalidLocaleCode:
        return None
    if source is not None and locale.same_as(source):
        return locale
    return LocaleCode.recognized(name)


def _named(stem: str, source: LocaleCode | None) -> tuple[str, LocaleCode] | None:
    """A locale file's name prefix and locale: `("", en)` for `en`, `("app_", en)` for
    `app_en`, `("app_", pt_BR)` for `app_pt_BR`; None when no part of it is a locale."""
    locale = _locale_of(stem, source)
    if locale is not None:
        return "", locale
    for separator in _PREFIX_END.finditer(stem):
        locale = _locale_of(stem[separator.end() :], source)
        if locale is not None:
            return stem[: separator.end()], locale
    return None


def _prefix(stem: str, source: LocaleCode) -> str:
    named = _named(stem, source)
    return named[0] if named is not None else ""


def _locales(names: Iterable[str]) -> tuple[LocaleCode, ...]:
    found = (LocaleCode.recognized(name) for name in sorted(names))
    return tuple(locale for locale in found if locale is not None)


def _bundle_locales(content: object) -> tuple[LocaleCode, ...]:
    """The locales of a bundle: each key a locale code, each value an object."""
    if not isinstance(content, dict) or not content:
        return ()
    locales = []
    for key, value in content.items():
        locale = LocaleCode.recognized(key)
        if locale is None or not isinstance(value, dict):
            return ()
        locales.append(locale)
    return tuple(locales)


def _choose_source(
    path: str, locales: tuple[LocaleCode, ...], source: LocaleCode | None
) -> LocaleCode:
    """The source among `locales`, keeping its spelling there: the one asked, else `en`, else
    the only one."""
    wanted = [source] if source is not None else [_DEFAULT_SOURCE]
    for candidate in wanted:
        for locale in locales:
            if locale.same_as(candidate):
                return locale
    if source is None and len(locales) == 1:
        return locales[0]
    asked = source.value if source is not None else None
    raise SourceLocaleUnknown(path, [locale.value for locale in locales], asked)


def _selected(name: str, include: tuple[str, ...], exclude: tuple[str, ...]) -> bool:
    if include and not any(fnmatch.fnmatch(name, pattern) for pattern in include):
        return False
    return not any(fnmatch.fnmatch(name, pattern) for pattern in exclude)


def _output(request: TreeRequest, default: Path) -> Path:
    return request.output.expanduser().resolve() if request.output is not None else default
