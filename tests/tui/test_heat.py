import pytest

from i18n_ai.cli.tui.kit.heat import shade


@pytest.mark.parametrize(
    ("percent", "step"),
    [(0, 0), (1, 1), (39, 1), (40, 2), (74, 2), (75, 3), (99, 3), (100, 4)],
)
def test_a_percentage_takes_its_step_on_the_heat_scale(percent: int, step: int) -> None:
    assert shade(percent) == step
