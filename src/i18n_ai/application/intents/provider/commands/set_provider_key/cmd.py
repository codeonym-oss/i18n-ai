from dataclasses import dataclass, field

from mediary.cqrs import Command, command

from .receipt import KeyReceipt


@command
@dataclass(frozen=True)
class SetProviderKeyCommand(Command[KeyReceipt]):
    """Give a provider its API key: saved in the system keyring when `save`, else used for this
    run only. A key that cannot be saved is used for the run, and the receipt tells why. Raises
    `ProviderUnknown`, or `ProviderTakesNoKey`."""

    provider: str
    key: str = field(repr=False)
    save: bool = False
