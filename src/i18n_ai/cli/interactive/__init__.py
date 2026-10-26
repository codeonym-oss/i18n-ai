"""The interactive mode. `generate` reads `is_interactive` and `prompter` from here, so tests
replace them with a terminal of their own."""

from ..common.setup import Choice, command_line
from .prompter import Prompter, QuestionaryPrompter
from .wizard import Wizard, is_interactive


def prompter() -> Prompter:
    return QuestionaryPrompter()


__all__ = [
    "Choice",
    "Prompter",
    "QuestionaryPrompter",
    "Wizard",
    "command_line",
    "is_interactive",
    "prompter",
]
