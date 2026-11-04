from dataclasses import dataclass, field

from mediary.cqrs import Command, command

from ......domain.exports.provider import ModelSpec
from .....ports.locale import MessageRef, TreeRequest
from ..generate_locales import GenerationOptions, GenerationReceipt


@command
@dataclass(frozen=True)
class RetryFallbacksCommand(Command[GenerationReceipt]):
    """Translate `messages` of the targets again with `model`, and keep the rest of each target
    as it is: the other fallbacks too. A message that fails again stays recorded, with its new
    rejected translation. The files are not classified again, and `options.overwrite` does not
    apply. A message whose source file is no longer in the tree is left out. Raises
    `LocaleTreeNotFound`, `SourceLocaleUnknown`, `MixedLocaleFormats`, `TargetIsSource`,
    `ProviderUnknown` or `ProviderNotInstalled`."""

    tree: TreeRequest
    model: ModelSpec
    messages: tuple[MessageRef, ...]
    options: GenerationOptions = field(default_factory=GenerationOptions)
