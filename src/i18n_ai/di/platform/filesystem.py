from dishka import Provider, Scope, provide

from ...application.ports.locale import ILocaleStore, ILocaleTreeScanner, IProjectInspector
from ...infra.adapters.filesystem import (
    FileSystemLocaleStore,
    FileSystemLocaleTreeScanner,
    FileSystemProjectInspector,
)


class FileSystemProvider(Provider):
    """The locale trees on disk: finding them, and reading and writing their documents; and the
    project around them, read for its i18n library."""

    scope = Scope.APP

    scanner = provide(FileSystemLocaleTreeScanner, provides=ILocaleTreeScanner)
    store = provide(FileSystemLocaleStore, provides=ILocaleStore)
    inspector = provide(FileSystemProjectInspector, provides=IProjectInspector)
