from typing import Any

from ....application.ports.locale import ILocaleStore
from ....domain.exports.locale import LocaleDocument, SourceFile, TargetLocation
from .formats import format_of, load_document


class FileSystemLocaleStore(ILocaleStore):
    """Target documents as files in their source's format; under a key, as one locale's key of
    a bundle, or of a file rooted at its locale."""

    async def read(self, location: TargetLocation) -> LocaleDocument | None:
        adapter = format_of(location.path)
        if adapter is None or not location.path.is_file():
            return None
        document, _ = load_document(location.path, adapter)
        if document is None or location.bundle_key is None:
            return document
        content = document.content.get(location.bundle_key)
        return LocaleDocument(content) if isinstance(content, dict) else None

    async def write(
        self, location: TargetLocation, content: dict[str, Any], like: SourceFile
    ) -> None:
        adapter = format_of(like.path)
        assert adapter is not None, f"{like.path} was read, so its format is known"
        adapter.write(location.path, content, like, location.bundle_key)
