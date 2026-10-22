from typing import Any

from ....application.ports.locale import ILocaleStore
from ....domain.exports.locale import JsonStyle, LocaleDocument, TargetLocation
from .json_io import dump, load_document, read_json, write_atomically


class FileSystemLocaleStore(ILocaleStore):
    """Target documents as JSON files; in a bundle, as one locale's key of the bundle file."""

    async def read(self, location: TargetLocation) -> LocaleDocument | None:
        if not location.path.is_file():
            return None
        document, _ = load_document(location.path)
        if document is None or location.bundle_key is None:
            return document
        content = document.content.get(location.bundle_key)
        return LocaleDocument(content, document.style) if isinstance(content, dict) else None

    async def write(
        self, location: TargetLocation, content: dict[str, Any], style: JsonStyle
    ) -> None:
        if location.bundle_key is None:
            write_atomically(location.path, dump(content, style))
            return
        # A bundle keeps its other locales, its order and its own style
        bundle: dict[str, Any] = {}
        if location.path.is_file():
            existing, style = read_json(location.path)
            if isinstance(existing, dict):
                bundle = existing
        bundle[location.bundle_key] = content
        write_atomically(location.path, dump(bundle, style))
