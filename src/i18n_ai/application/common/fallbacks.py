from collections.abc import Iterable
from pathlib import Path, PurePosixPath

from ...domain.exports.locale import KeyPath, TargetLocation
from ..ports.locale import RecordedFallback


def record_target(directory: Path, location: TargetLocation) -> tuple[PurePosixPath, str | None]:
    """A target in the record: its file, relative to the record's directory, and its key."""
    return PurePosixPath(location.path.relative_to(directory).as_posix()), location.bundle_key


def recorded_paths(
    recorded: Iterable[RecordedFallback], place: tuple[PurePosixPath, str | None]
) -> list[KeyPath]:
    """The messages recorded as fallbacks in the target at `place`."""
    return [entry.path for entry in recorded if entry.target == place]
