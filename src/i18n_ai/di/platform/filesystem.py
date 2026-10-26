from dishka import Provider, Scope, provide

from ...application.ports.locale import (
    IFallbackRecord,
    ILocaleStore,
    ILocaleTreeScanner,
    IProjectInspector,
)
from ...infra.adapters.filesystem import (
    FileSystemFallbackRecord,
    FileSystemLocaleStore,
    FileSystemLocaleTreeScanner,
    FileSystemProjectInspector,
)


class FileSystemProvider(Provider):
    """The locale trees on disk: finding them, and reading and writing their documents and
    their fallback record; and the project around them, read for its i18n library."""

    scope = Scope.APP

    scanner = provide(FileSystemLocaleTreeScanner, provides=ILocaleTreeScanner)
    store = provide(FileSystemLocaleStore, provides=ILocaleStore)
    fallbacks = provide(FileSystemFallbackRecord, provides=IFallbackRecord)
    inspector = provide(FileSystemProjectInspector, provides=IProjectInspector)
