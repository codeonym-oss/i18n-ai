from dataclasses import dataclass

from mediary.cqrs import Command, command

from ......domain.exports.locale import LocaleCode
from ......domain.exports.provider import ModelSpec
from .....ports.locale import TreeRequest
from .receipt import GenerationReceipt


@dataclass(frozen=True)
class GenerationOptions:
    """How to generate.

    - `overwrite`: translate every message again, instead of keeping the existing target's good
      translations.
    - `strict`: write no file that has a message which kept failing the rules; otherwise such a
      message keeps its source text, and is reported.
    The others are the engine's (see `EngineSettings`)."""

    context: str | None = None
    batch_size: int = 40
    concurrency: int = 8
    max_attempts: int = 3
    classify: bool = True
    overwrite: bool = False
    strict: bool = False
    temperature: float | None = None


@command
@dataclass(frozen=True)
class GenerateLocalesCommand(Command[GenerationReceipt]):
    """Generate the `targets` of a locale tree from its source with `model`, and write them.
    Raises `LocaleTreeNotFound`, `SourceLocaleUnknown`, `MixedLocaleFormats`, `TargetIsSource`,
    `ProviderUnknown`, or `ProviderNotInstalled` (see `InstallProviderCommand`)."""

    tree: TreeRequest
    targets: tuple[LocaleCode, ...]
    model: ModelSpec
    options: GenerationOptions = GenerationOptions()
