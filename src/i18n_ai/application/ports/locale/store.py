from abc import ABC, abstractmethod
from typing import Any

from ....domain.exports.locale import LocaleDocument, SourceFile, TargetLocation


class ILocaleStore(ABC):
    """Reads and writes the target locales' documents."""

    @abstractmethod
    async def read(self, location: TargetLocation) -> LocaleDocument | None:
        """The document at `location`, or None if there is none or it is not an object."""
        raise NotImplementedError

    @abstractmethod
    async def write(
        self, location: TargetLocation, content: dict[str, Any], like: SourceFile
    ) -> None:
        """Write `content` to `location` the way `like`, its source file, is written: its format,
        indent, quoting and comments where the format has them. Makes the directories; under its
        key, keeps the file's other keys."""
        raise NotImplementedError
