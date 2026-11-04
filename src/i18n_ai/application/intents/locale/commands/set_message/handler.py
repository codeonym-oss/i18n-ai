from dataclasses import replace

from mediary.cqrs import CommandHandler, command_handler

from ......domain.exports.locale import (
    MessageUnknown,
    TargetNotGenerated,
    check,
    errors,
    extract_schema,
    normalize,
    qualify,
)
from .....common import record_target, validated_targets
from .....ports.locale import IFallbackRecord, ILocaleStore, ILocaleTreeScanner
from .cmd import SetMessageCommand
from .result import MessageSet


@command_handler
class SetMessageCommandHandler(CommandHandler[SetMessageCommand, MessageSet]):
    """Check the text against the source's message, write it in the target, and take the
    message out of the record."""

    def __init__(
        self, scanner: ILocaleTreeScanner, store: ILocaleStore, fallbacks: IFallbackRecord
    ) -> None:
        self._scanner = scanner
        self._store = store
        self._fallbacks = fallbacks

    async def handle(self, command: SetMessageCommand) -> MessageSet:
        message = command.message
        name, target, path = str(message.file), message.target.value, str(message.path)

        # 1. The source's message, and the target's document
        tree = await self._scanner.scan(replace(command.tree, include=(), exclude=()))
        validated_targets(tree, (message.target,))
        file = next((file for file in tree.files if file.name == message.file), None)
        if file is None or not qualify(file.document, file.error).qualifies:
            raise MessageUnknown(name, target, path)
        assert file.document is not None
        location = tree.target_location(message.target, file)
        document = await self._store.read(location)
        if document is None:
            raise TargetNotGenerated(name, target)
        schema = extract_schema(file.document, tree.source, message.target, tree.syntax)
        unit = next((unit for unit in schema.units if unit.path == message.path), None)
        if unit is None:
            raise MessageUnknown(name, target, path)

        # 2. The text, refused when it breaks a rule
        text = normalize(unit, command.text)
        violations = check(schema, unit, text)
        if errors(violations):
            return MessageSet(written=False, violations=tuple(violations))

        # 3. Written, and no longer a fallback
        await self._store.write(location, document.with_value(message.path, text).content, file)
        directory = tree.target_directory
        place = record_target(directory, location)
        recorded = await self._fallbacks.read(directory)
        kept = tuple(
            entry for entry in recorded if (entry.target, entry.path) != (place, message.path)
        )
        if len(kept) != len(recorded):
            await self._fallbacks.write(directory, kept)
        return MessageSet(written=True, violations=tuple(violations))
