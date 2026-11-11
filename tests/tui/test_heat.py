import pytest
from textual.content import Content

from i18n_ai.cli.tui.kit.heat import shade, strip


@pytest.mark.parametrize(
    ("percent", "step"),
    [(0, 0), (1, 1), (39, 1), (40, 2), (74, 2), (75, 3), (99, 3), (100, 4)],
)
def test_a_percentage_takes_its_step_on_the_heat_scale(percent: int, step: int) -> None:
    assert shade(percent) == step


def runs(content: Content) -> list[tuple[str, int]]:
    return [(str(span.style), span.end - span.start) for span in content.spans]


@pytest.mark.parametrize(
    ("counts", "expected"),
    [
        ((10, 0, 10), [("$secondary", 5), ("$border-strong", 5)]),
        ((1, 0, 399), [("$secondary", 1), ("$border-strong", 9)]),
        ((10, 3, 0), [("$warning", 3), ("$secondary", 7)]),
        ((0, 0, 14), [("$border-strong", 10)]),
        ((3, 3, 0), [("$warning", 10)]),
    ],
    ids=["half", "one-of-400", "fallbacks", "all-kept", "all-fallbacks"],
)
def test_a_strip_is_its_messages_in_proportion(
    counts: tuple[int, int, int], expected: list[tuple[str, int]]
) -> None:
    to_translate, fallbacks, kept = counts
    content = strip(10, to_translate, fallbacks, kept)

    assert len(content) == 10
    assert runs(content) == expected


def test_a_strip_off_is_muted() -> None:
    assert runs(strip(10, 10, 3, 10, off=True)) == [("$border-blurred", 10)]


def test_a_file_with_no_message_has_an_empty_strip() -> None:
    assert len(strip(10, 0, 0, 0)) == 0


def test_a_strip_narrower_than_its_runs_keeps_its_width() -> None:
    assert len(strip(1, 10, 3, 5)) == 1


def test_a_strip_takes_no_more_fallbacks_than_messages_to_translate() -> None:
    assert runs(strip(10, 2, 5, 0)) == [("$warning", 10)]
