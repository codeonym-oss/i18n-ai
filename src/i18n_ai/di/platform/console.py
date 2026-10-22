from dishka import Provider, Scope, from_context
from rich.console import Console


class ConsoleProvider(Provider):
    """The terminal: the CLI's console, given as context."""

    scope = Scope.APP

    console = from_context(provides=Console, scope=Scope.APP)
