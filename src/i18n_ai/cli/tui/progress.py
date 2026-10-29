from textual.message import Message
from textual.message_pump import MessagePump

from ...application.exports.locale import ProgressEvent
from ...application.ports.progress import IGenerationProgress


class TuiProgress(IGenerationProgress):
    """A generation's progress, each event posted as a message to the screen that shows it, its
    `target`; nothing is shown without one."""

    class Event(Message):
        def __init__(self, event: ProgressEvent) -> None:
            super().__init__()
            self.event = event

    def __init__(self) -> None:
        self.target: MessagePump | None = None

    def on(self, event: ProgressEvent) -> None:
        if self.target is not None:
            self.target.post_message(self.Event(event))
