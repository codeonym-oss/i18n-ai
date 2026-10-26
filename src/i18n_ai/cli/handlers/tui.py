from pathlib import Path

from ..common.runner import valid_settings


def tui() -> None:
    """Open the full-screen TUI: set a generation up as a form, run it, and read its receipt."""
    # Textual is loaded only for the TUI
    from ..tui import run_tui

    run_tui(valid_settings(), Path.cwd())
