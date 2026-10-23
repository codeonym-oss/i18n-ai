from dataclasses import dataclass

from mediary.cqrs import Command, command

from .receipt import KeyRemoval


@command
@dataclass(frozen=True)
class RemoveProviderKeyCommand(Command[KeyRemoval]):
    """Remove a provider's API key from the system keyring. Raises `ProviderUnknown`,
    `ProviderTakesNoKey`, or `KeyringUnavailable`."""

    provider: str
