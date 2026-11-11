from textual.widgets import Static

# The upper bound of each step but the last: 0, 1–39, 40–74, 75–99, 100
_STEPS = (0, 39, 74, 99)


def percent(part: int, whole: int) -> int:
    """`part` of `whole`, rounded down: 100 only when nothing is left."""
    return part * 100 // whole if whole else 0


def shade(percent: int) -> int:
    """The step of the heat scale, 0 to 4, that `percent` takes."""
    return next((step for step, top in enumerate(_STEPS) if percent <= top), len(_STEPS))


class HeatCell(Static):
    """A cell of a heatmap: its percentage, shaded on the heat scale, and a note beside it."""

    def __init__(self, percent: int, note: str = "") -> None:
        text = f"{percent}%" if percent else "—"
        content = f"{text}  {note}" if note else text
        super().__init__(content, classes=f"heat -heat-{shade(percent)}")
