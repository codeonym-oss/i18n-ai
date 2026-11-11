from textual.content import Content
from textual.widgets import Static

# The upper bound of each step but the last: 0, 1–39, 40–74, 75–99, 100
_STEPS = (0, 39, 74, 99)
STRIP = "▆"
# A strip's runs, in order: what each counts, and its colour
RUNS = (("fallback again", "$warning"), ("to translate", "$secondary"), ("kept", "$border-strong"))


def percent(part: int, whole: int) -> int:
    """`part` of `whole`, rounded down: 100 only when nothing is left."""
    return part * 100 // whole if whole else 0


def strip(width: int, to_translate: int, fallbacks: int, kept: int, off: bool = False) -> Content:
    """A file's messages across `width`, in proportion: its recorded `fallbacks` in amber (no
    more than the ones to translate), the rest `to_translate` in sky, the `kept` ones dark; each
    part there takes one cell at least, while there is room. Muted when the cell is `off`, empty
    when the file has no message."""
    fallbacks = min(fallbacks, to_translate)
    counts = (fallbacks, to_translate - fallbacks, kept)
    total = sum(counts)
    if not total or width <= 0:
        return Content("")
    if off:
        return Content.styled(STRIP * width, "$border-blurred")
    sizes = [max(1, number * width // total) if number else 0 for number in counts]
    while sum(sizes) > width:  # narrower than its parts
        sizes[sizes.index(max(sizes))] -= 1
    sizes[counts.index(max(counts))] += width - sum(sizes)
    return Content.assemble(
        *((STRIP * size, style) for size, (_, style) in zip(sizes, RUNS, strict=True) if size)
    )


def legend() -> Content:
    """What the strip's colours mean."""
    return Content("  ").join(Content.assemble((STRIP, style), f" {word}") for word, style in RUNS)


def shade(percent: int) -> int:
    """The step of the heat scale, 0 to 4, that `percent` takes."""
    return next((step for step, top in enumerate(_STEPS) if percent <= top), len(_STEPS))


class HeatCell(Static):
    """A cell of a heatmap: its percentage, shaded on the heat scale, and a note beside it."""

    def __init__(self, percent: int, note: str = "") -> None:
        text = f"{percent}%" if percent else "—"
        content = f"{text}  {note}" if note else text
        super().__init__(content, classes=f"heat -heat-{shade(percent)}")
