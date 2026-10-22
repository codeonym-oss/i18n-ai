import logging
from types import TracebackType
from typing import Self

from dishka import AsyncContainer
from mediary import Mediator
from rich.console import Console

from ..runtime.settings import Settings
from .container import build_container
from .messaging import build_mediator

logger = logging.getLogger(__name__)


class Bootstrap:
    """Wires every handler to the mediator, builds the container, and opens one request scope
    for the command the CLI runs; leaving closes both.

        async with Bootstrap(settings, console) as bootstrap:
            report = await bootstrap.mediator.send(ScanLocaleTreeQuery(...))"""

    def __init__(self, settings: Settings, console: Console) -> None:
        self.settings = settings
        self.console = console
        self._container: AsyncContainer | None = None
        self._request: AsyncContainer | None = None
        self._mediator: Mediator | None = None

    @property
    def mediator(self) -> Mediator:
        if self._mediator is None:
            raise RuntimeError("Bootstrap is not entered")
        return self._mediator

    async def __aenter__(self) -> Self:
        # 1. Wire every handler, then build the container that provides them
        self._container = build_container(build_mediator(), self.console)

        # 2. Open the request scope, and its mediator
        self._request = await self._container().__aenter__()
        self._mediator = await self._request.get(Mediator)
        logger.debug("Every handler is wired")
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        if self._request is not None:
            await self._request.close()
        if self._container is not None:
            await self._container.close()
