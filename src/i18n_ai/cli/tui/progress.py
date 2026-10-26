from textual.message import Message
from textual.message_pump import MessagePump

from ...application.ports.progress import IGenerationProgress


class TuiProgress(IGenerationProgress):
    """A generation's progress, posted as messages to the screen that shows it, its `target`;
    nothing is shown without one."""

    class Started(Message):
        def __init__(self, jobs: int) -> None:
            super().__init__()
            self.jobs = jobs

    class Dropped(Message):
        def __init__(self, jobs: int, reason: str) -> None:
            super().__init__()
            self.jobs = jobs
            self.reason = reason

    class Advanced(Message):
        def __init__(self, description: str) -> None:
            super().__init__()
            self.description = description

    def __init__(self) -> None:
        self.target: MessagePump | None = None

    def start(self, jobs: int) -> None:
        self._post(self.Started(jobs))

    def drop(self, jobs: int, reason: str) -> None:
        self._post(self.Dropped(jobs, reason))

    def advance(self, description: str) -> None:
        self._post(self.Advanced(description))

    def finish(self) -> None:
        """The receipt that follows says it."""

    def _post(self, message: Message) -> None:
        if self.target is not None:
            self.target.post_message(message)
