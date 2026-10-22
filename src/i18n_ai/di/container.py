from dishka import AsyncContainer, Provider, make_async_container
from mediary import Mediator
from mediary.ext.dishka import MediaryProvider
from rich.console import Console

from .platform import ConsoleProvider, FileSystemProvider, LangChainProvider, PackagesProvider


def build_container(mediator: Mediator, console: Console, *overrides: Provider) -> AsyncContainer:
    """The composition root. The platform's adapters live as long as the app; each intent's
    handler is made per request, with its ports resolved from them. `overrides` come last, so
    they replace what they provide (tests swap the model out this way)."""
    return make_async_container(
        # 1. Platform
        FileSystemProvider(),
        LangChainProvider(),
        PackagesProvider(),
        ConsoleProvider(),
        # 2. Messaging: the handlers, and a mediator per request that resolves them
        MediaryProvider(mediator),
        # 3. Overrides
        *overrides,
        context={Console: console},
    )
