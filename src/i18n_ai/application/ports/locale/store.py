from abc import ABC, abstractmethod
from typing import Any

from ....domain.exports.locale import JsonStyle, LocaleDocument, TargetLocation


class ILocaleStore(ABC):
    """Reads and writes the target locales' documents."""

    @abstractmethod
    async def read(self, location: TargetLocation) -> LocaleDocument | None:
        """The document at `location`, or None if there is none or it is not a JSON object."""
        raise NotImplementedError

    @abstractmethod
    async def write(
        self, location: TargetLocation, content: dict[str, Any], style: JsonStyle
    ) -> None:
        """Write `content` to `location`, making its directories; in a bundle, under its key,
        keeping the other locales."""
        raise NotImplementedError
