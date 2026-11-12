"""The plan screen: its cells, the inspector on the focused one, the run bar, and the cells
turned off before a run."""

from pathlib import Path

from textual.widgets import Static

from i18n_ai.application.exports.locale import ScanReport, SourceFileView, TargetView
from i18n_ai.cli.tui.kit.shell import ShellScreen
from i18n_ai.cli.tui.kit.widgets import PlanCell, RunCell
from i18n_ai.cli.tui.plan import PlanScreen
from i18n_ai.cli.tui.run import RunScreen
from i18n_ai.cli.tui.setup import SetupScreen
from support.fakes import FakeGateway
from support.tui import ended, fallen, on_cell, planning, ready, running, settle, tui


def cells(plan: PlanScreen) -> list[list[str]]:
    """A row per file: its name, then each cell as the plan reads it."""
    rows: dict[str, list[str]] = {}
    for cell in plan.query(PlanCell):
        rows.setdefault(cell.file, [cell.file]).append(cell.text)
    return list(rows.values())


def shown(screen: ShellScreen[object], selector: str) -> str:
    return str(screen.query_one(selector, Static).content)


def inspector(plan: PlanScreen) -> str:
    return f"{plan.query_one('#inspector').border_title}\n{shown(plan, '#inspected')}"


def receipt(run: RunScreen) -> str:
    return shown(run, "#again-text")


async def test_the_plan_shows_each_file_and_locale(isolated: Path, vault: object) -> None:
    app = tui(isolated)
    async with app.run_test(size=(160, 45)) as pilot:
        await running(pilot)
        await ready(pilot, "de")

        plan = await planning(pilot)

        assert cells(plan) == [
            ["auth/login.json", "new 10", "new 9"],
            ["common.json", "fill 13", "new 15"],
        ]
        assert shown(plan, "#total") == "47 messages · 4 agents · 4 calls of ≤40"
        assert "4 of 4 cells on" in shown(plan, "#status-tree")
        assert "left out · meta.json" in shown(plan, ".left-out")


async def test_the_arrows_move_between_cells_and_the_inspector_follows(
    isolated: Path, vault: object
) -> None:
    app = tui(isolated)
    async with app.run_test(size=(160, 45)) as pilot:
        await running(pilot)
        await ready(pilot, "de")
        plan = await planning(pilot)
        assert inspector(plan).startswith("Inspector · auth/login.json → fr\nnew · 10 to translate")

        for key in ("right", "right", "down", "down"):  # past the edges: it stays
            await pilot.press(key)
        await pilot.pause()

        focused = plan.focused
        assert isinstance(focused, PlanCell)
        assert (focused.file, focused.locale) == ("common.json", "de")
        assert inspector(plan).startswith("Inspector · common.json → de\nnew · 15 to translate")
        assert "locales/de/common.json" in inspector(plan)
        assert "no recorded fallback" in inspector(plan)


async def test_the_inspector_shows_a_cells_recorded_fallbacks(
    isolated: Path, vault: object, gateway: FakeGateway
) -> None:
    await fallen(isolated, gateway, "app.welcome")
    app = tui(isolated)
    async with app.run_test(size=(160, 45)) as pilot:
        await running(pilot)
        await ready(pilot)
        plan = await planning(pilot)

        await on_cell(pilot, plan, 1, 0, "left")  # common.json → fr, where it fell back

        assert "app.welcome  FALLBACK" in inspector(plan)
        assert "Welcome back" in inspector(plan)
        strip = list(plan.query(PlanCell))[1].query_one(".cell-strip")
        assert "$warning" in [str(span.style) for span in strip.render().spans]  # type: ignore[union-attr]


async def test_a_cell_a_row_or_a_column_turns_off(isolated: Path, vault: object) -> None:
    app = tui(isolated)
    async with app.run_test(size=(160, 45)) as pilot:
        await running(pilot)
        await ready(pilot, "de")
        plan = await planning(pilot)

        await on_cell(pilot, plan, 1, 1, "space")
        assert cells(plan)[1] == ["common.json", "fill 13", "off"]
        assert shown(plan, "#total") == "32 messages · 3 agents · 3 calls of ≤40"
        assert "3 of 4 cells on · common.json → de off" in shown(plan, "#status-tree")

        await on_cell(pilot, plan, 0, 0, "c")
        assert cells(plan) == [
            ["auth/login.json", "off", "new 9"],
            ["common.json", "off", "off"],
        ]

        await on_cell(pilot, plan, 1, 0, "r")  # all off already: back on
        assert cells(plan)[1] == ["common.json", "fill 13", "new 15"]
        assert shown(plan, "#total") == "37 messages · 3 agents · 3 calls of ≤40"
        await on_cell(pilot, plan, 0, 0, "r")
        assert cells(plan)[0] == ["auth/login.json", "off", "off"]


async def test_the_plan_runs_nothing_with_every_cell_off(isolated: Path, vault: object) -> None:
    app = tui(isolated)
    async with app.run_test(size=(100, 40)) as pilot:
        await running(pilot)
        await ready(pilot)
        plan = await planning(pilot)

        await on_cell(pilot, plan, 0, 0, "c")
        await pilot.press("ctrl+r")
        await pilot.pause()

        assert app.screen is plan
        assert any("Every cell is off" in str(n.message) for n in app._notifications)

        await pilot.press("b")
        await settle(pilot)
        assert isinstance(app.screen, SetupScreen)


async def test_a_cell_turned_off_is_not_written(isolated: Path, vault: object) -> None:
    app = tui(isolated)
    async with app.run_test(size=(120, 40)) as pilot:
        await running(pilot)
        await ready(pilot, "de")
        plan = await planning(pilot)

        await on_cell(pilot, plan, 1, 1, "space")
        await pilot.press("ctrl+r")
        run = await ended(pilot)

        assert (isolated / "locales/de/auth/login.json").is_file()
        assert not (isolated / "locales/de/common.json").exists()
        assert "$ i18n-ai generate locales -t fr,de -m openai:fake-model" in (receipt(run))
        assert "1 single cell was off; this command runs it too." in receipt(run)


async def test_a_row_off_is_excluded_in_the_command(isolated: Path, vault: object) -> None:
    app = tui(isolated)
    async with app.run_test(size=(140, 40)) as pilot:
        await running(pilot)
        await ready(pilot)
        plan = await planning(pilot)

        await on_cell(pilot, plan, 1, 0, "r")
        await pilot.click("#run")
        run = await ended(pilot)

        assert "-m openai:fake-model --exclude common.json" in receipt(run)
        assert "single cell" not in receipt(run)
        common = [cell.text for cell in run.query(RunCell) if cell.file == "common.json"]
        assert common == ["off"]


async def test_the_plan_fits_80_columns(isolated: Path, vault: object) -> None:
    app = tui(isolated)
    async with app.run_test(size=(80, 24)) as pilot:
        await running(pilot)
        await ready(pilot, "de", "es", "it", "ja")
        plan = await planning(pilot)

        for selector in ("#cells", "#inspector", "#total", "Footer"):
            field = plan.query_one(selector)
            assert field.region.width > 0, selector
            assert field.region.right <= 80, selector
            assert 0 < field.region.bottom <= 24, selector

        for _ in range(4):
            await pilot.press("right")
        await pilot.pause()
        focused = plan.focused
        assert isinstance(focused, PlanCell)
        assert focused.locale == "ja"
        assert focused.region.right <= 80  # scrolled to it
        head = plan.query(".column-head")[-1]
        assert "ja" in str(head.query_one(Static).content)
        assert head.region.x == focused.region.x  # the header scrolled with the cells
        await pilot.press("down")
        await pilot.pause()
        file = plan.query(".file-head")[-1]
        assert file.region.y == plan.focused.region.y  # type: ignore[union-attr]


async def test_a_plan_with_no_file_takes_its_keys(isolated: Path) -> None:
    report = ScanReport(
        root=isolated,
        layout="directory",
        format="json",
        source="en",
        source_name="English",
        source_path=isolated,
        output=isolated,
        existing=("en",),
        files=(SourceFileView("meta.json", isolated, False, "it looks like data", 0),),
        targets=(TargetView("fr", "French", "ltr", True, ()),),
    )
    app = tui(isolated)
    async with app.run_test(size=(100, 40)) as pilot:
        await running(pilot)
        plan = PlanScreen(report)
        await app.push_screen(plan)
        await pilot.pause()

        for key in ("space", "r", "c", "ctrl+r"):
            await pilot.press(key)
            await pilot.pause()

        assert app.screen is plan
        assert shown(plan, "#total") == "0 messages · 0 agents · 0 calls of ≤40"
        assert "no file to translate" in shown(plan, "#inspected")
