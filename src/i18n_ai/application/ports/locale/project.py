from abc import ABC, abstractmethod
from pathlib import Path

from ....domain.exports.locale import ConfigHint


class IProjectInspector(ABC):
    """Reads what a project reveals of its i18n library: its dependencies, its files, and what
    its config files say. Nothing is run; the files are read as text."""

    @abstractmethod
    async def dependencies(self, root: Path) -> dict[str, str]:
        """The packages the project's manifests at `root` depend on, lowercased, each with the
        manifest naming it: `{"react-i18next": "package.json"}`."""
        raise NotImplementedError

    @abstractmethod
    async def find(self, root: Path, pattern: str) -> str | None:
        """The first file under `root` matching the glob `pattern`, relative to it."""
        raise NotImplementedError

    @abstractmethod
    async def configured(self, root: Path, hint: ConfigHint) -> tuple[Path, str] | None:
        """The existing directory a config file names as the locales', and the file's name."""
        raise NotImplementedError

    @abstractmethod
    async def is_directory(self, path: Path) -> bool:
        raise NotImplementedError
