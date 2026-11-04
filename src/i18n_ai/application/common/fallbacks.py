from collections.abc import Iterable
from pathlib import Path, PurePosixPath

from ...domain.exports.locale import KeyPath, TargetLocation
from ..ports.locale import FallbackProblem, FileTranslated, RecordedFallback


def record_target(directory: Path, location: TargetLocation) -> tuple[PurePosixPath, str | None]:
    """A target in the record: its file, relative to the record's directory, and its key."""
    return PurePosixPath(location.path.relative_to(directory).as_posix()), location.bundle_key


def recorded_paths(
    recorded: Iterable[RecordedFallback], place: tuple[PurePosixPath, str | None]
) -> list[KeyPath]:
    """The messages recorded as fallbacks in the target at `place`."""
    return [entry.path for entry in recorded if entry.target == place]


def recorded_fallbacks(
    place: tuple[PurePosixPath, str | None], event: FileTranslated
) -> list[RecordedFallback]:
    """The fallbacks `event` wrote at `place`, as the record keeps them."""
    file, key = place
    return [
        RecordedFallback(
            file,
            key,
            path,
            tuple(
                FallbackProblem(violation.code, violation.message)
                for violation in event.failures
                if violation.path == path
            ),
            rejected,
        )
        for path, rejected in event.rejected.items()
    ]
