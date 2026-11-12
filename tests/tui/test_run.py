"""The run screen: each job live in the plan's grid, the progress in messages, the events feed
and its pop-ups, stop, and the receipt it becomes."""

import asyncio
import json
import time
from pathlib import Path

import pytest
from textual.app import App, ComposeResult
from textual.pilot import Pilot
from textual.widgets import Static

from i18n_ai.application.exports.locale import (
    FileResult,
    JobDone,
    JobRetrying,
    JobStarted,
    ResultStatus,
    RunStarted,
)
from i18n_ai.cli.tui.kit.widgets import KpiTile, RunCell
from i18n_ai.cli.tui.run import RunScreen
from i18n_ai.cli.tui.setup import SetupScreen
from i18n_ai.domain.exports.locale import KeyPath, Violation, ViolationCode
from support.fakes import FakeGateway
from support.tui import (
    ended,
    on_cell,
    pick,
    planning,
    post,
    ready,
    running,
    scripted,
    settle,
    tui,
)


def welcome() -> Violation:
    message = "the placeholders differ: missing {{name}}"
    return Violation("u1", KeyPath(("app", "welcome")), ViolationCode.PLACEHOLDERS, message)


def cells(run: RunScreen) -> list[list[str]]:
    """A row per file: its name, then each cell as the run reads it."""
    rows: dict[str, list[str]] = {}
    for cell in run.query(RunCell):
        rows.setdefault(cell.file, [cell.file]).append(cell.text)
    return list(rows.values())


def shown(run: RunScreen, selector: str) -> str:
    return str(run.query_one(selector, Static).content)


def feed(run: RunScreen, problems: bool = False) -> list[str]:
    """The feed's lines, newest first; only those shown under `problems`."""
    lines = run.query_one("#feed").query(".event").results(Static)
    return [str(line.content) for line in lines if not problems or line.has_class("-problem")]


async def through(pilot: Pilot[None], *targets: str) -> RunScreen:
    """A run of the example into fr and `targets`, from the setup through the plan, ended."""
    await running(pilot)
    await ready(pilot, *targets)
    await planning(pilot)
    await pilot.press("ctrl+r")
    return await ended(pilot)


class OneCell(App[None]):
    def compose(self) -> ComposeResult:
        yield RunCell("common.json", "fr")


@pytest.mark.parametrize(
    ("args", "tag", "text"),
    [
        (("waiting",), "◌ WAITING", "waiting"),
        (("retry", "2/3"), "⟳ RETRY 2/3", "retry 2/3"),
        (("written",), "● WRITTEN", "written"),
        (("partial",), "◐ PARTIAL", "partial"),
        (("failed",), "✕ FAILED", "failed"),
        (("stopped",), "■ STOPPED", "stopped"),
        (("off",), "— OFF", "off"),
    ],
)
async def test_a_run_cell_shows_its_jobs_state(args: tuple[str, ...], tag: str, text: str) -> None:
    async with OneCell().run_test() as pilot:
        cell = pilot.app.query_one(RunCell)
        cell.show(*args, detail="12 translated · 26 kept", note="after 2 attempts")

        assert cell.text == text
        assert str(cell.query_one(".cell-tag", Static).content) == tag
        assert str(cell.query_one(".cell-detail", Static).content) == "12 translated · 26 kept"
        assert cell.has_class(f"-{args[0]}")


async def test_a_run_writes_the_targets_and_says_how_to_run_it_again(
    isolated: Path, vault: object
) -> None:
    app = tui(isolated)
    async with app.run_test(size=(120, 40)) as pilot:
        run = await through(pilot)

        assert "$ i18n-ai generate locales -t fr -m openai:fake-model" in shown(run, "#again-text")
        assert "Generated with openai:fake-model" in feed(run)[0]
        french = json.loads((isolated / "locales/fr/common.json").read_text(encoding="utf-8"))
        assert french["app"]["welcome"]
        assert cells(run) == [["auth/login.json", "written"], ["common.json", "written"]]

        await pilot.press("b")
        await settle(pilot)
        assert isinstance(app.screen, SetupScreen)


async def test_a_retry_shows_in_its_cell_as_it_happens(
    isolated: Path, vault: object, gateway: FakeGateway, monkeypatch: pytest.MonkeyPatch
) -> None:
    gateway.broken_first = {"app.welcome"}
    seen: list[tuple[str, str, str]] = []
    show = RunCell.show

    def watched(cell: RunCell, *args: str, **kwargs: str) -> None:
        show(cell, *args, **kwargs)
        seen.append((cell.file, cell.locale, cell.text))

    monkeypatch.setattr(RunCell, "show", watched)
    app = tui(isolated)
    async with app.run_test(size=(120, 40)) as pilot:
        run = await through(pilot)

        common = [text for file, locale, text in seen if (file, locale) == ("common.json", "fr")]
        assert common == ["waiting", "translating", "retry 2/3", "written"]
        assert "1 message sent back · attempt 2/3" in "\n".join(feed(run))


async def test_a_dropped_file_shows_as_it_happens(
    isolated: Path, vault: object, gateway: FakeGateway
) -> None:
    gateway.refuse = {"common.json"}
    app = tui(isolated)
    async with app.run_test(size=(120, 40)) as pilot:
        run = await through(pilot)

        assert cells(run)[1] == ["common.json", "ignored"]
        assert any("common.json\nignored · fake" in line for line in feed(run))
        assert any("common.json is ignored" in str(n.title) for n in app._notifications)
        assert "1/1 jobs" in shown(run, "#progress-line")


async def test_a_partial_file_tells_its_fallbacks_and_why(
    isolated: Path, vault: object, gateway: FakeGateway
) -> None:
    gateway.broken_first = {"app.welcome"}
    app = tui(isolated, attempts=1)
    async with app.run_test(size=(120, 40)) as pilot:
        run = await through(pilot)

        assert cells(run)[1] == ["common.json", "partial"]
        partial = next(line for line in feed(run) if "partial · 1 fallback" in line)
        assert "  app.welcome · " in partial  # its reason follows
        assert any("is partial" in str(n.title) for n in app._notifications)
        written = next(line for line in feed(run) if "auth/login.json → fr" in line)
        assert written.endswith("locales/fr/auth/login.json")

        await pilot.press("p")
        assert run.query_one("#events").border_title == "Events · problems"
        assert all("written ·" not in line for line in feed(run, problems=True))
        assert any("partial · 1 fallback" in line for line in feed(run, problems=True))


async def test_a_warning_shows_under_its_job(
    isolated: Path, vault: object, gateway: FakeGateway
) -> None:
    gateway.unchanged = {"nav.logout"}
    app = tui(isolated)
    async with app.run_test(size=(120, 40)) as pilot:
        run = await through(pilot)

        line = next(line for line in feed(run) if "common.json → fr" in line and "written" in line)
        assert "! 1 warning\n  nav.logout · left as in the source" in line
        assert line in feed(run, problems=True)


async def test_the_run_shows_waiting_cells_and_the_ones_off(isolated: Path, vault: object) -> None:
    app = tui(isolated)
    async with app.run_test(size=(120, 40)) as pilot:
        await running(pilot)
        await ready(pilot, "de")
        plan = await planning(pilot)
        await on_cell(pilot, plan, 1, 1, "space")

        await pilot.press("ctrl+r")
        run = await ended(pilot)

        assert cells(run) == [
            ["auth/login.json", "written", "written"],
            ["common.json", "written", "off"],
        ]


async def test_a_run_goes_from_waiting_to_written(
    isolated: Path, vault: object, gateway: FakeGateway, monkeypatch: pytest.MonkeyPatch
) -> None:
    classified, translated = asyncio.Event(), asyncio.Event()
    classify, translate = gateway.classify, gateway.translate

    async def held_classify(file, source):  # type: ignore[no-untyped-def]
        await classified.wait()
        return await classify(file, source)

    async def held_translate(batch):  # type: ignore[no-untyped-def]
        await translated.wait()
        return await translate(batch)

    monkeypatch.setattr(gateway, "classify", held_classify)
    monkeypatch.setattr(gateway, "translate", held_translate)
    app = tui(isolated)
    async with app.run_test(size=(120, 40)) as pilot:
        await running(pilot)
        await ready(pilot)
        await planning(pilot)
        await pilot.press("ctrl+r")
        run = await showing(pilot, "waiting")
        assert cells(run) == [["auth/login.json", "waiting"], ["common.json", "waiting"]]

        classified.set()
        await showing(pilot, "translating", every=True)

        translated.set()
        await ended(pilot)
        assert cells(run) == [["auth/login.json", "written"], ["common.json", "written"]]


async def showing(pilot: Pilot[None], text: str, every: bool = False) -> RunScreen:
    """The run screen, once one of its cells (or `every` one) reads `text`."""
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        screen = pilot.app.screen
        if isinstance(screen, RunScreen) and screen.is_mounted:
            states = [cell for row in cells(screen) for cell in row[1:]]
            if (all if every else any)(state == text for state in states):
                return screen
        await pilot.pause(0.05)
    raise AssertionError(f"no cell reads {text!r}")


async def test_the_progress_counts_messages_and_the_time(isolated: Path) -> None:
    app = tui(isolated)
    async with app.run_test(size=(160, 45)) as pilot:
        run, times = await scripted(pilot, "fr", "de")
        login = (isolated / "locales/fr/auth/login.json").resolve()
        times.append(42.0)
        await post(
            pilot,
            run,
            RunStarted(4),
            JobStarted("auth/login.json", "fr"),
            JobRetrying("common.json", "fr", 1, 2, 3),
            JobDone(FileResult("auth/login.json", "fr", login, ResultStatus.WRITTEN, 10, 0)),
            JobDone(FileResult("common.json", "de", None, ResultStatus.FAILED, reason="boom")),
            JobDone(
                FileResult(
                    "common.json", "fr", None, ResultStatus.PARTIAL, 12, 3, failures=(welcome(),)
                )
            ),
            JobStarted("added-since-the-plan.json", "fr"),  # not in the grid: no cell, no fall
        )

        # 10 of auth/login.json → fr, 13 of common.json → fr and 15 of common.json → de, of 47
        assert shown(run, "#done-percent") == "80%"
        assert shown(run, "#progress-line") == "3/4 jobs · 38/47 messages · ⟳ 1 ◐ 1 ✕ 1 · 00:42"
        status = str(run.query_one("#status-tree", Static).content)
        assert status.startswith("RUNNING · 3/4 jobs · 00:42")
        assert any(line.startswith("00:42 ✕ common.json → de\nfailed · boom") for line in feed(run))
        assert "added-since-the-plan.json → fr" in feed(run)[0]
        assert [span.style for span in run.query_one("#bar").render().spans] == [  # type: ignore[union-attr]
            "$success",
            "$warning",
            "$error",
            "$border-strong",
        ]
        titles = [str(n.title) for n in app._notifications]
        assert "common.json → de is failed" in titles
        assert "common.json → fr is partial" in titles


async def test_the_end_is_the_receipt(isolated: Path, vault: object, gateway: FakeGateway) -> None:
    gateway.broken_first = {"app.welcome"}
    app = tui(isolated, attempts=1)
    async with app.run_test(size=(160, 45)) as pilot:
        run = await through(pilot)

        tiles = {
            str(tile.query_one(".kpi-label", Static).content): str(
                tile.query_one(".kpi-value", Static).content
            )
            for tile in run.query(KpiTile)
        }
        assert tiles == {"FILES WRITTEN": "2", "TRANSLATED": "22", "FALLBACKS": "1", "FAILED": "0"}
        assert not run.query_one("#progress").display
        assert "y copy · v review 1 fallback" in shown(run, "#again-text")
        heads = [str(head.content) for head in run.query(".column-head-count").results(Static)]
        assert heads == ["2/2"]

        assert any(str(n.title) == "The run is over" for n in app._notifications)

        await pilot.press("y")
        assert app.clipboard == "i18n-ai generate locales -t fr -m openai:fake-model"
        # Sent to the terminal, which may not copy it: the notice does not claim it did
        notice = str(list(app._notifications)[-1].message)
        assert notice.startswith("Asked your terminal to copy the command.")


async def test_ctrl_c_stops_the_run_and_keeps_what_is_written(
    isolated: Path, vault: object, gateway: FakeGateway, monkeypatch: pytest.MonkeyPatch
) -> None:
    translate = gateway.translate
    held = asyncio.Event()

    async def one_then_held(batch):  # type: ignore[no-untyped-def]
        if "common" in batch.file:
            await held.wait()
        return await translate(batch)

    monkeypatch.setattr(gateway, "translate", one_then_held)
    common = (isolated / "locales/fr/common.json").read_text(encoding="utf-8")
    app = tui(isolated)
    async with app.run_test(size=(160, 45)) as pilot:
        await running(pilot)
        await ready(pilot)
        await planning(pilot)
        await pilot.press("ctrl+r")
        run = await showing(pilot, "written")
        assert run.check_action("stop", ())

        await pilot.press("ctrl+c")
        await ended(pilot)

        assert cells(run) == [["auth/login.json", "written"], ["common.json", "stopped"]]
        assert (isolated / "locales/fr/auth/login.json").is_file()
        assert (isolated / "locales/fr/common.json").read_text(encoding="utf-8") == common
        assert feed(run)[0].endswith("stopped\n1 of 2 jobs done")
        assert "$ i18n-ai generate locales -t fr" in shown(run, "#again-text")
        assert not run.check_action("stop", ())  # the app's ctrl+c again
        assert any(str(n.title) == "The run stopped" for n in app._notifications)

        await pilot.press("b")
        await settle(pilot)
        assert isinstance(app.screen, SetupScreen)
        held.set()
        # The key given for the run lists the models again, and clears the pick (a follow-up)
        await pick(pilot, "#model", "fake-model")
        await planning(pilot)
        await pilot.press("ctrl+r")
        again = await ended(pilot)  # a fresh run goes again
        assert cells(again) == [["auth/login.json", "written"], ["common.json", "written"]]


async def test_the_run_fits_80_columns(isolated: Path) -> None:
    app = tui(isolated)
    async with app.run_test(size=(80, 24)) as pilot:
        run, _ = await scripted(pilot, "fr", "de", "es", "it", "ja")
        await post(pilot, run, RunStarted(10), JobStarted("common.json", "ja"))

        for selector in ("#progress", "#grid-card", "#events", "Footer"):
            field = run.query_one(selector)
            assert field.region.width > 0, selector
            assert field.region.right <= 80, selector
            assert 0 < field.region.bottom <= 24, selector
        assert shown(run, "#progress-line").startswith("0% · 0/10 jobs")
        assert run.query_one("#progress").region.height == 3  # the bar and its line, one line

        for _ in range(4):
            await pilot.press("right")
        await pilot.pause()
        focused = run.focused
        assert isinstance(focused, RunCell)
        assert focused.locale == "ja"
        head = run.query(".column-head")[-1]
        assert head.region.x == focused.region.x  # the header scrolled with the cells
