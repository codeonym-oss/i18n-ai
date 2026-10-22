"""Finding a locale tree from the path a user gives:

- a locale directory, `locales/en`: the directory layout, its siblings the other locales;
- a locale file, `messages/en.json`: the file layout, its siblings the other locales;
- a bundle, `i18n.json` holding `{"en": {...}, "fr": {...}}`: the bundle layout;
- the directory holding the locales, `locales/`: whichever of the first two it holds, with the
  source named, or `en` when there is one, or the only locale."""

import fnmatch
from collections.abc import Iterable
from pathlib import Path, PurePosixPath

from ....application.ports.locale import ILocaleTreeScanner, TreeRequest
from ....domain.exports.locale import (
    InvalidLocaleCode,
    LocaleCode,
    LocaleDocument,
    LocaleTree,
    LocaleTreeNotFound,
    SourceFile,
    SourceLocaleUnknown,
    TreeLayout,
)
from .json_io import load_document, read_json

_SKIPPED = {"node_modules", "__pycache__", "dist", "build"}
_DEFAULT_SOURCE = LocaleCode("en")


class FileSystemLocaleTreeScanner(ILocaleTreeScanner):
    async def scan(self, request: TreeRequest) -> LocaleTree:
        path = request.path.expanduser().resolve()
        if not path.exists():
            raise LocaleTreeNotFound(str(path), "it does not exist")
        if path.is_file():
            return self._from_file(path, request)
        return self._from_directory(path, request)

    # The path is a file: a locale file, or a bundle

    def _from_file(self, path: Path, request: TreeRequest) -> LocaleTree:
        if path.suffix.lower() != ".json":
            raise LocaleTreeNotFound(str(path), "it is not a JSON file")
        locale = _locale_of(path.stem, request.source)
        if locale is not None:
            return self._file_layout(path.parent, path, locale, request)

        try:
            content, style = read_json(path)
        except (OSError, ValueError) as error:
            raise LocaleTreeNotFound(str(path), f"it is not valid JSON ({error})") from error
        locales = _bundle_locales(content)
        if not locales:
            raise LocaleTreeNotFound(
                str(path), "its name is not a locale code, and its keys are not locales"
            )
        source = _choose_source(str(path), locales, request.source)
        document = LocaleDocument(content[source.value], style)
        return LocaleTree(
            root=path,
            layout=TreeLayout.BUNDLE,
            source=source,
            files=(SourceFile(PurePosixPath(path.name), path, document),),
            existing=tuple(locale for locale in locales if not locale.same_as(source)),
            output=_output(request, path),
        )

    def _file_layout(
        self, root: Path, path: Path, source: LocaleCode, request: TreeRequest
    ) -> LocaleTree:
        document, error = load_document(path)
        siblings = [file for file in root.glob(f"*{path.suffix}") if file.is_file()]
        existing = _locales(file.stem for file in siblings if file != path)
        return LocaleTree(
            root=root,
            layout=TreeLayout.FILE,
            source=source,
            files=(SourceFile(PurePosixPath(path.name), path, document, error),),
            existing=existing,
            output=_output(request, root),
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

        files = {child.stem: child for child in path.glob("*.json") if child.is_file()}
        locale_files = _locales(files)
        if locale_files:
            source = _choose_source(str(path), locale_files, request.source)
            return self._file_layout(path, files[source.value], source, request)

        raise LocaleTreeNotFound(
            str(path), "it holds no locale directory (en/) and no locale file (en.json)"
        )

    def _directory_layout(
        self, root: Path, directory: Path, source: LocaleCode, request: TreeRequest
    ) -> LocaleTree:
        files: list[SourceFile] = []
        for path in sorted(directory.rglob("*.json")):
            relative = path.relative_to(directory)
            if any(part.startswith(".") or part in _SKIPPED for part in relative.parts[:-1]):
                continue
            name = PurePosixPath(relative.as_posix())
            if not _selected(str(name), request.include, request.exclude):
                continue
            document, error = load_document(path)
            files.append(SourceFile(name, path, document, error))
        siblings = (child.name for child in root.iterdir() if child.is_dir() and child != directory)
        return LocaleTree(
            root=root,
            layout=TreeLayout.DIRECTORY,
            source=source,
            files=tuple(files),
            existing=_locales(siblings),
            output=_output(request, root),
        )


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
