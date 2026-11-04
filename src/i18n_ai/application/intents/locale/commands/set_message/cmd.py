from dataclasses import dataclass

from mediary.cqrs import Command, command

from .....ports.locale import MessageRef, TreeRequest
from .result import MessageSet


@command
@dataclass(frozen=True)
class SetMessageCommand(Command[MessageSet]):
    """Set `message` of a target to `text`, by hand. The text is checked against the rules as a
    model's would be: one that breaks them is refused, and nothing changes. Once written, the
    message is no longer a fallback. Raises `LocaleTreeNotFound`, `SourceLocaleUnknown`,
    `MixedLocaleFormats`, `TargetIsSource`, `MessageUnknown` when the source file has no such
    message, or `TargetNotGenerated` when the target has no version of the file yet."""

    tree: TreeRequest
    message: MessageRef
    text: str
