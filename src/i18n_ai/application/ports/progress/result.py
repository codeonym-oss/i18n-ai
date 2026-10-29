from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from ....domain.exports.locale import Violation


class ResultStatus(StrEnum):
    WRITTEN = "written"  # every message passed the rules
    PARTIAL = "partial"  # written, with the failed messages in their source text
    REFUSED = "refused"  # not written: some messages failed, and the generation is strict
    IGNORED = "ignored"  # the file is not a locale document
    FAILED = "failed"  # the file could not be translated


@dataclass(frozen=True)
class FileResult:
    """What became of one source file, in one target unless it was ignored."""

    file: str
    target: str | None
    path: Path | None
    status: ResultStatus
    translated: int = 0
    reused: int = 0
    reason: str | None = None
    failures: tuple[Violation, ...] = ()
    warnings: tuple[Violation, ...] = ()
