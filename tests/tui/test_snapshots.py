"""The screens as they look, as SVG under `__snapshots__/`: a change in how one looks fails
here until `--snapshot-update` writes it again, after a look at the new SVG."""

from pathlib import Path

import pytest
from textual.pilot import Pilot

from support.fakes import FakeGateway
from support.tui import Snap, fallen, tui

SIZES = [(160, 45), (80, 24)]


async def to_setup(pilot: Pilot[None]) -> None:
    await pilot.press("ctrl+n")


@pytest.mark.parametrize("size", SIZES, ids=["160x45", "80x24"])
async def test_home(isolated: Path, snap: Snap, size: tuple[int, int]) -> None:
    await snap(tui(isolated), size)


async def test_home_with_a_fallback(isolated: Path, snap: Snap, gateway: FakeGateway) -> None:
    await fallen(isolated, gateway, "app.welcome")
    await snap(tui(isolated), (160, 45))


@pytest.mark.parametrize("size", SIZES, ids=["160x45", "80x24"])
async def test_setup(isolated: Path, snap: Snap, size: tuple[int, int]) -> None:
    await snap(tui(isolated), size, to_setup)


async def test_a_small_terminal(isolated: Path, snap: Snap) -> None:
    await snap(tui(isolated), (70, 20))
