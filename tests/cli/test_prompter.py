"""The terminal's prompts, driven by keys through a pipe."""

from collections.abc import Iterator

import pytest
from prompt_toolkit.input import PipeInput, create_pipe_input
from prompt_toolkit.output import DummyOutput

from i18n_ai.cli.interactive import Choice, QuestionaryPrompter

DOWN, ENTER = "\x1b[B", "\r"
CHOICES = [Choice("a", "Apple"), Choice("b", "Banana"), Choice("c", "Cherry")]


@pytest.fixture
def keys() -> Iterator[PipeInput]:
    with create_pipe_input() as pipe:
        yield pipe


@pytest.fixture
def prompter(keys: PipeInput) -> QuestionaryPrompter:
    return QuestionaryPrompter(input=keys, output=DummyOutput())


async def test_select(keys: PipeInput, prompter: QuestionaryPrompter) -> None:
    keys.send_text(DOWN + ENTER)

    assert await prompter.select("Fruit?", CHOICES, default="b") == "c"


async def test_a_long_list_is_searched(keys: PipeInput, prompter: QuestionaryPrompter) -> None:
    many = [Choice(f"{n}", f"locale {n}") for n in range(20)]
    keys.send_text("17" + ENTER)

    assert await prompter.select("Which?", many, default="not there") == "17"


async def test_checkbox(keys: PipeInput, prompter: QuestionaryPrompter) -> None:
    keys.send_text(" " + DOWN + DOWN + " " + ENTER)

    assert await prompter.checkbox("Fruits?", CHOICES, checked={"b"}) == ["a", "b", "c"]


async def test_text_secret_and_confirm(keys: PipeInput, prompter: QuestionaryPrompter) -> None:
    keys.send_text("  locales  " + ENTER)
    assert await prompter.text("Path?") == "locales"

    keys.send_text("sk-123" + ENTER)
    assert await prompter.secret("Key?") == "sk-123"

    keys.send_text("n")
    assert await prompter.confirm("Go?") is False
