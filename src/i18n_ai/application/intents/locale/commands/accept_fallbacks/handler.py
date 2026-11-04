from dataclasses import replace

from mediary.cqrs import CommandHandler, command_handler

from .....ports.locale import IFallbackRecord, ILocaleTreeScanner
from .cmd import AcceptFallbacksCommand


@command_handler
class AcceptFallbacksCommandHandler(CommandHandler[AcceptFallbacksCommand, None]):
    """Write the record without the accepted entries, found by their target and path."""

    def __init__(self, scanner: ILocaleTreeScanner, fallbacks: IFallbackRecord) -> None:
        self._scanner = scanner
        self._fallbacks = fallbacks

    async def handle(self, command: AcceptFallbacksCommand) -> None:
        tree = await self._scanner.scan(replace(command.tree, include=(), exclude=()))
        accepted = {(entry.target, entry.path) for entry in command.entries}
        recorded = await self._fallbacks.read(tree.target_directory)
        kept = tuple(entry for entry in recorded if (entry.target, entry.path) not in accepted)
        if len(kept) != len(recorded):
            await self._fallbacks.write(tree.target_directory, kept)
