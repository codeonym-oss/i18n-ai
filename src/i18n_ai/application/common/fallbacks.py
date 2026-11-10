from collections.abc import Iterable
from pathlib import Path, PurePosixPath

from ...domain.exports.locale import (
    KeyPath,
    LocaleCode,
    LocaleTree,
    SourceFile,
    TargetLocation,
    qualify,
)
from ..ports.locale import FallbackProblem, FileTranslated, RecordedFallback

_Place = tuple[PurePosixPath, str | None]


def record_target(directory: Path, location: TargetLocation) -> _Place:
    """A target in the record: its file, relative to the record's directory, and its key."""
    return PurePosixPath(location.path.relative_to(directory).as_posix()), location.bundle_key


def record_targets(tree: LocaleTree) -> dict[_Place, tuple[SourceFile, LocaleCode, TargetLocation]]:
    """The targets the record may name, by their place in it: every qualifying source file in
    every locale the tree has. An entry that matches none has no target."""
    targets: dict[_Place, tuple[SourceFile, LocaleCode, TargetLocation]] = {}
    for file in tree.files:
        if not qualify(file.document, file.error).qualifies:
            continue
        for locale in tree.existing:
            if not locale.same_as(tree.source):
                location = tree.target_location(locale, file)
                targets[record_target(tree.target_directory, location)] = (file, locale, location)
    return targets


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
