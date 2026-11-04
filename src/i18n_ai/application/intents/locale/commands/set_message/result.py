from dataclasses import dataclass

from ......domain.exports.locale import Violation


@dataclass(frozen=True)
class MessageSet:
    """What became of a text: `written`, or refused for the errors among its `violations`; a
    written one may still have warnings."""

    written: bool
    violations: tuple[Violation, ...]
