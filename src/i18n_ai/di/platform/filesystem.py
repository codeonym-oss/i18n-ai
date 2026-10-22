from dishka import Provider, Scope, provide

from ...application.ports.locale import ILocaleStore, ILocaleTreeScanner
from ...infra.adapters.filesystem import FileSystemLocaleStore, FileSystemLocaleTreeScanner


class FileSystemProvider(Provider):
    """The locale trees on disk: finding them, and reading and writing their documents."""

    scope = Scope.APP

    scanner = provide(FileSystemLocaleTreeScanner, provides=ILocaleTreeScanner)
    store = provide(FileSystemLocaleStore, provides=ILocaleStore)
