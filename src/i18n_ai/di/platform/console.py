from dishka import Provider, Scope, from_context, provide
from rich.console import Console

from ...application.ports.progress import IGenerationProgress
from ...infra.adapters.console import RichGenerationProgress


class ConsoleProvider(Provider):
    """The terminal: the CLI's console, given as context, and the progress shown on it."""

    scope = Scope.APP

    console = from_context(provides=Console, scope=Scope.APP)
    progress = provide(RichGenerationProgress, provides=IGenerationProgress)


class GivenProgress(Provider):
    """The progress the app was given, shown in place of the console's: the TUI's own."""

    scope = Scope.APP

    def __init__(self, progress: IGenerationProgress) -> None:
        super().__init__()
        self._progress = progress

    @provide
    def progress(self) -> IGenerationProgress:
        return self._progress
