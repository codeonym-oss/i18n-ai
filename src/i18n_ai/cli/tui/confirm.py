from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Static


class ConfirmScreen(ModalScreen[bool]):
    """A yes or no question over the screen."""

    DEFAULT_CSS = """
    ConfirmScreen { align: center middle; }
    ConfirmScreen > Vertical {
        width: 60; height: auto; border: round $accent; padding: 1 2; background: $surface;
    }
    ConfirmScreen Horizontal { height: auto; margin-top: 1; }
    ConfirmScreen Button { margin-right: 2; }
    """
    BINDINGS = [
        Binding("y", "answer(True)", "Yes"),
        Binding("n,escape", "answer(False)", "No"),
    ]

    def __init__(self, question: str) -> None:
        super().__init__()
        self.question = question

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Static(self.question)
            with Horizontal():
                yield Button("Yes", id="yes", variant="primary", compact=True)
                yield Button("No", id="no", compact=True)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(event.button.id == "yes")

    def action_answer(self, yes: bool) -> None:
        self.dismiss(yes)
