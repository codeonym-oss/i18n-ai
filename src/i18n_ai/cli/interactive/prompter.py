from abc import ABC, abstractmethod
from collections.abc import Collection, Sequence
from dataclasses import dataclass
from typing import Any

import questionary

# A list longer than this can be searched by typing.
_SEARCHABLE = 10


@dataclass(frozen=True)
class Choice:
    value: str
    title: str


class Prompter(ABC):
    """Asks the user. Ctrl-C raises `KeyboardInterrupt`."""

    @abstractmethod
    async def select(
        self, message: str, choices: Sequence[Choice], default: str | None = None
    ) -> str:
        raise NotImplementedError

    @abstractmethod
    async def checkbox(
        self, message: str, choices: Sequence[Choice], checked: Collection[str] = ()
    ) -> list[str]:
        """At least one choice."""
        raise NotImplementedError

    @abstractmethod
    async def text(self, message: str, default: str = "") -> str:
        raise NotImplementedError

    @abstractmethod
    async def secret(self, message: str) -> str:
        """Typed without echo."""
        raise NotImplementedError

    @abstractmethod
    async def confirm(self, message: str, default: bool = True) -> bool:
        raise NotImplementedError


class QuestionaryPrompter(Prompter):
    """The terminal's prompts, with questionary. `options` go to prompt_toolkit's application
    (tests give it a pipe as `input`)."""

    def __init__(self, **options: Any) -> None:
        self._options = options

    async def select(
        self, message: str, choices: Sequence[Choice], default: str | None = None
    ) -> str:
        searchable = len(choices) > _SEARCHABLE
        question = questionary.select(
            message,
            choices=[questionary.Choice(choice.title, choice.value) for choice in choices],
            default=default if any(choice.value == default for choice in choices) else None,
            use_search_filter=searchable,
            use_jk_keys=not searchable,
            instruction="(type to search, ↑↓ to move)" if searchable else None,
            **self._options,
        )
        return str(await question.unsafe_ask_async())

    async def checkbox(
        self, message: str, choices: Sequence[Choice], checked: Collection[str] = ()
    ) -> list[str]:
        question = questionary.checkbox(
            message,
            choices=[
                questionary.Choice(choice.title, choice.value, checked=choice.value in checked)
                for choice in choices
            ],
            validate=lambda picked: bool(picked) or "Pick at least one",
            use_search_filter=True,
            use_jk_keys=False,
            instruction="(type to search, space to pick, enter to confirm)",
            **self._options,
        )
        return [str(value) for value in await question.unsafe_ask_async()]

    async def text(self, message: str, default: str = "") -> str:
        question = questionary.text(message, default=default, **self._options)
        return str(await question.unsafe_ask_async()).strip()

    async def secret(self, message: str) -> str:
        question = questionary.password(message, **self._options)
        return str(await question.unsafe_ask_async()).strip()

    async def confirm(self, message: str, default: bool = True) -> bool:
        question = questionary.confirm(message, default=default, **self._options)
        return bool(await question.unsafe_ask_async())
