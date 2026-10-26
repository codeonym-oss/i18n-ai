import json
import logging
from pathlib import Path, PurePosixPath
from typing import Any

from ....application.ports.locale import FallbackProblem, IFallbackRecord, RecordedFallback
from ....domain.exports.locale import KeyPath, ViolationCode
from .files import read_text, write_atomically

logger = logging.getLogger(__name__)

FILE_NAME = ".i18n-ai-fallbacks.json"
_VERSION = 1


class FileSystemFallbackRecord(IFallbackRecord):
    """The record as `.i18n-ai-fallbacks.json`, committed with the locales: a list sorted by
    file, key and path, so that a run changes only the lines of what it changed. A path is its
    segments, since a key may hold dots."""

    async def read(self, directory: Path) -> tuple[RecordedFallback, ...]:
        path = directory / FILE_NAME
        if not path.is_file():
            return ()
        try:
            content = json.loads(read_text(path)[0])
            if content.get("version") != _VERSION:
                raise ValueError(f"version {content.get('version')!r}, not {_VERSION}")
            return tuple(_entry(item) for item in content["fallbacks"])
        except (OSError, ValueError, KeyError, TypeError, AttributeError) as error:
            logger.warning("%s cannot be read, and is left out: %s", path, error)
            return ()

    async def write(self, directory: Path, entries: tuple[RecordedFallback, ...]) -> None:
        path = directory / FILE_NAME
        if not entries:
            path.unlink(missing_ok=True)
            return
        ordered = sorted(
            entries, key=lambda entry: (str(entry.file), entry.key or "", _order(entry.path))
        )
        content = {"version": _VERSION, "fallbacks": [_item(entry) for entry in ordered]}
        write_atomically(path, json.dumps(content, ensure_ascii=False, indent=2) + "\n")


def _item(entry: RecordedFallback) -> dict[str, Any]:
    item: dict[str, Any] = {"file": str(entry.file)}
    if entry.key is not None:
        item["key"] = entry.key
    item["path"] = list(entry.path.segments)
    item["problems"] = [
        {"rule": problem.rule.value, "message": problem.message} for problem in entry.problems
    ]
    item["rejected"] = entry.rejected
    return item


def _entry(item: dict[str, Any]) -> RecordedFallback:
    return RecordedFallback(
        file=PurePosixPath(item["file"]),
        key=item.get("key"),
        path=KeyPath(tuple(item["path"])),
        problems=tuple(
            FallbackProblem(ViolationCode(problem["rule"]), problem["message"])
            for problem in item["problems"]
        ),
        rejected=item["rejected"],
    )


def _order(path: KeyPath) -> tuple[tuple[int, int, str], ...]:
    """Indexes in their order, before keys: a path's segments mix both."""
    return tuple(
        (0, segment, "") if isinstance(segment, int) else (1, 0, segment)
        for segment in path.segments
    )
