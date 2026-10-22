from dataclasses import dataclass

from ....contract.exceptions.generic import EmptyValueProvided


@dataclass(frozen=True)
class ModelSpec:
    """The model to translate with, as LangChain's `init_chat_model` takes it: `provider:model`
    (`openai:gpt-4.1-mini`, `ollama:qwen2.5:14b`), or a model name its provider is known from
    (`claude-sonnet-4-5`)."""

    value: str

    def __post_init__(self) -> None:
        value = self.value.strip()
        if not value:
            raise EmptyValueProvided(name="model")
        object.__setattr__(self, "value", value)

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class ResolvedModel:
    """A model spec with its provider known: the provider's name, the model's name, and the
    Python package that integrates the provider with LangChain."""

    provider: str
    model: str
    package: str
    module: str

    @property
    def spec(self) -> str:
        return f"{self.provider}:{self.model}"
