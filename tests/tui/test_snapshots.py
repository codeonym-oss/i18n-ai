"""The screens as they look, as SVG under `__snapshots__/`: a change in how one looks fails
here until `--snapshot-update` writes it again, after a look at the new SVG."""

from collections.abc import Awaitable, Callable
from pathlib import Path

import pytest
from textual.pilot import Pilot

from support.fakes import FakeGateway
from support.tui import Snap, fallen, on_cell, pick, planning, ready, settle, tui

SIZES = [(160, 45), (80, 24)]


async def to_targets(pilot: Pilot[None]) -> None:
    await pilot.press("ctrl+n")
    await settle(pilot)


async def to_tree(pilot: Pilot[None]) -> None:
    await to_targets(pilot)
    await pilot.click("#step-tree")
    await settle(pilot)


async def to_model(pilot: Pilot[None]) -> None:
    await to_targets(pilot)
    await pilot.click("#step-model")
    await pick(pilot, "#provider", "openai")
    await pick(pilot, "#model", "fake-model")


@pytest.mark.parametrize("size", SIZES, ids=["160x45", "80x24"])
async def test_home(isolated: Path, snap: Snap, size: tuple[int, int]) -> None:
    await snap(tui(isolated), size)


async def test_home_with_a_fallback(isolated: Path, snap: Snap, gateway: FakeGateway) -> None:
    await fallen(isolated, gateway, "app.welcome")
    await snap(tui(isolated), (160, 45))


@pytest.mark.parametrize("size", SIZES, ids=["160x45", "80x24"])
@pytest.mark.parametrize("step", [to_tree, to_targets, to_model], ids=["tree", "targets", "model"])
async def test_setup(
    isolated: Path,
    snap: Snap,
    size: tuple[int, int],
    step: Callable[[Pilot[None]], Awaitable[None]],
) -> None:
    await snap(tui(isolated), size, step)


async def to_plan(pilot: Pilot[None]) -> None:
    """The plan into fr and de, auth/login.json → de off, on the cell with a fallback."""
    await to_targets(pilot)
    await ready(pilot, "de")
    plan = await planning(pilot)
    await on_cell(pilot, plan, 0, 1, "space")
    await on_cell(pilot, plan, 1, 0, "left")


@pytest.mark.parametrize("size", SIZES, ids=["160x45", "80x24"])
async def test_plan(
    isolated: Path, snap: Snap, size: tuple[int, int], vault: object, gateway: FakeGateway
) -> None:
    await fallen(isolated, gateway, "app.welcome")
    await snap(tui(isolated), size, to_plan)


async def to_plan_scrolled(pilot: Pilot[None]) -> None:
    """The plan into five locales, on the last one: the headers and the files stay."""
    await to_targets(pilot)
    await ready(pilot, "de", "es", "it", "ja")
    await planning(pilot)
    for key in ("right", "right", "right", "right", "down"):
        await pilot.press(key)


async def test_plan_scrolled(isolated: Path, snap: Snap, vault: object) -> None:
    await snap(tui(isolated), (80, 24), to_plan_scrolled)


async def test_a_small_terminal(isolated: Path, snap: Snap) -> None:
    await snap(tui(isolated), (70, 20))
