"""The review screen: the fallbacks listed, the one under the cursor beside them with its
source, the model's last attempt, its text now and the other locales' ones, and an editor whose
text is checked when it is saved."""

import json
from pathlib import Path

from textual.pilot import Pilot
from textual.widgets import DataTable, Input, Static

from i18n_ai.cli.tui.review import ReviewScreen
from i18n_ai.cli.tui.setup import SetupScreen
from support.fakes import FakeGateway
from support.tui import ended, fallen, planning, ready, running, settle, tui

RECORD = "locales/.i18n-ai-fallbacks.json"


async def reviewing(pilot: Pilot[None]) -> ReviewScreen:
    await pilot.press("v")
    await settle(pilot)
    screen = pilot.app.screen
    assert isinstance(screen, ReviewScreen)
    return screen


def rows(screen: ReviewScreen) -> list[list[str]]:
    grid = screen.query_one(DataTable)
    return [[str(cell) for cell in grid.get_row_at(i)] for i in range(grid.row_count)]


def shown(screen: ReviewScreen, selector: str) -> str:
    """The text a widget shows, its markup aside."""
    return "\n".join(
        str(widget.render())
        for widget in screen.query(f"{selector}, {selector} Static")
        if isinstance(widget, Static) and widget.display and str(widget.render())
    )


def french(project: Path) -> dict:  # type: ignore[type-arg]
    return json.loads((project / "locales/fr/common.json").read_text(encoding="utf-8"))


async def save(pilot: Pilot[None], text: str) -> None:
    """Into the editor, the text typed in, and enter."""
    await pilot.press("e")
    await settle(pilot)
    editor = pilot.app.screen.query_one("#text", Input)
    assert editor.has_focus
    editor.value = text
    await pilot.press("enter")
    await settle(pilot)


async def test_the_setup_says_fallbacks_are_recorded_and_opens_their_review(
    isolated: Path, gateway: FakeGateway
) -> None:
    await fallen(isolated, gateway, "app.welcome")
    app = tui(isolated)
    async with app.run_test(size=(160, 45)) as pilot:
        await running(pilot)
        line = app.screen.query_one("#fallbacks", Static)
        assert line.display
        assert str(line.content) == "1 fallback recorded · v to review"
        assert "Review fallbacks" in [c.title for c in app.get_system_commands(app.screen)]

        review = await reviewing(pilot)

        assert rows(review) == [["", "fr/common.json", "app.welcome", "placeholders"]]
        assert shown(review, "#where") == "fr/common.json · app.welcome"
        assert shown(review, "#rule") == "✕ placeholders"
        assert shown(review, "#position") == "1 of 1"
        assert shown(review, "#source .text") == "Welcome back, {{name}}!"
        assert shown(review, "#model .text") == "[fr] Welcome back, !"
        assert shown(review, "#model .problem") == "✕ missing {{name}}"
        assert shown(review, "#now .text") == "Welcome back, {{name}}!"
        assert review.query_one("#text", Input).value == "Welcome back, {{name}}!"
        assert shown(review, "#check") == "✕ placeholders · enter checks and saves"
        assert shown(review, "#elsewhere-text") == "no other locale"
        assert review.query_one("#hint").display  # no model picked: retry is off
        assert review.check_action("retry", ()) is None


async def test_the_same_key_elsewhere_shows_the_other_locales(
    isolated: Path, gateway: FakeGateway
) -> None:
    await fallen(isolated, gateway, "app.welcome")
    german = isolated / "locales/de/common.json"
    german.parent.mkdir()
    german.write_text(json.dumps({"app": {"title": "Acme"}}), encoding="utf-8")
    (isolated / "locales/it").mkdir()
    italian = isolated / "locales/it/common.json"
    italian.write_text(json.dumps({"app": {"welcome": "Bentornato, {{name}}!"}}), "utf-8")
    app = tui(isolated)
    async with app.run_test(size=(160, 45)) as pilot:
        await running(pilot)
        review = await reviewing(pilot)

        assert shown(review, "#elsewhere-text") == "de  —\nit  Bentornato, {{name}}!"


async def test_an_edit_is_checked_then_written(isolated: Path, gateway: FakeGateway) -> None:
    await fallen(isolated, gateway, "app.welcome")
    app = tui(isolated)
    async with app.run_test(size=(160, 45)) as pilot:
        await running(pilot)
        review = await reviewing(pilot)
        before = french(isolated)

        await save(pilot, "Bon retour !")

        assert shown(review, "#check") == "✕ missing {{name}}"
        assert review.query_one("#check").has_class("-refused")
        assert french(isolated) == before

        review.query_one("#text", Input).value = "Bon retour, {{name}} !"
        await pilot.press("enter")
        await settle(pilot)

        assert app.screen is review
        assert rows(review) == []
        assert review.query_one("#empty").display
        assert french(isolated)["app"]["welcome"] == "Bon retour, {{name}} !"
        assert not (isolated / RECORD).exists()

        await pilot.press("b")
        await settle(pilot)
        assert isinstance(app.screen, SetupScreen)
        assert not app.screen.query_one("#fallbacks").display


async def test_a_saved_fix_moves_on_to_the_next_fallback(
    isolated: Path, gateway: FakeGateway
) -> None:
    await fallen(isolated, gateway, "app.welcome", "cart.total")
    app = tui(isolated)
    async with app.run_test(size=(160, 45)) as pilot:
        await running(pilot)
        review = await reviewing(pilot)
        assert shown(review, "#position") == "1 of 2"

        await save(pilot, "Bon retour, {{name}} !")

        assert [row[2] for row in rows(review)] == ["cart.total"]
        assert shown(review, "#where") == "fr/common.json · cart.total"
        assert review.query_one("#text", Input).has_focus


async def test_escape_leaves_the_editor_then_the_review(
    isolated: Path, gateway: FakeGateway
) -> None:
    await fallen(isolated, gateway, "app.welcome")
    app = tui(isolated)
    async with app.run_test(size=(160, 45)) as pilot:
        await running(pilot)
        review = await reviewing(pilot)
        await pilot.press("e")
        await pilot.press("b")  # typed, not Back
        assert review.query_one("#text", Input).value.endswith("b")

        await pilot.press("escape")
        await settle(pilot)
        assert app.screen is review
        assert review.query_one(DataTable).has_focus

        await pilot.press("escape")
        await settle(pilot)
        assert isinstance(app.screen, SetupScreen)


async def test_the_marked_fallbacks_are_retried_with_the_forms_model(
    isolated: Path, gateway: FakeGateway
) -> None:
    await fallen(isolated, gateway, "app.welcome", "cart.total")
    app = tui(isolated)
    async with app.run_test(size=(160, 45)) as pilot:
        await running(pilot)
        await ready(pilot)
        review = await reviewing(pilot)
        assert len(rows(review)) == 2
        await pilot.press("space", "down", "space")
        assert [row[0] for row in rows(review)] == ["●", "●"]
        assert shown(review, "#position") == "2 of 2 · 2 marked"

        await pilot.press("r")
        await settle(pilot)

        sent = sorted(str(unit.path) for batch in gateway.batches for unit in batch.units)
        assert sent == ["app.welcome", "cart.total"]
        assert rows(review) == []
        assert french(isolated)["app"]["welcome"] == "[fr] Welcome back, {{name}}!"
        assert not (isolated / RECORD).exists()


async def test_accepting_the_highlighted_fallback_leaves_the_others(
    isolated: Path, gateway: FakeGateway
) -> None:
    await fallen(isolated, gateway, "app.welcome", "cart.total")
    app = tui(isolated)
    async with app.run_test(size=(160, 45)) as pilot:
        await running(pilot)
        review = await reviewing(pilot)

        await pilot.press("a")
        await settle(pilot)

        assert [row[2] for row in rows(review)] == ["cart.total"]
        assert french(isolated)["app"]["welcome"] == "Welcome back, {{name}}!"


async def test_a_run_that_leaves_a_fallback_opens_its_review_and_an_edit_fixes_it(
    isolated: Path, vault: object, gateway: FakeGateway
) -> None:
    gateway.broken_first = {"app.welcome"}
    app = tui(isolated, attempts=1)
    async with app.run_test(size=(120, 40)) as pilot:
        await running(pilot)
        await ready(pilot)
        await planning(pilot)
        await pilot.press("ctrl+r")
        run = await ended(pilot)
        assert run.reviewable

        review = await reviewing(pilot)
        assert [row[2] for row in rows(review)] == ["app.welcome"]
        await save(pilot, "Bon retour, {{name}} !")

        assert rows(review) == []
        assert not (isolated / RECORD).exists()
        for name in ("common.json", "auth/login.json"):
            assert (isolated / "locales/fr" / name).is_file()
        assert french(isolated)["app"]["welcome"] == "Bon retour, {{name}} !"
        await pilot.press("b")
        await settle(pilot)
        assert app.screen is run


async def test_a_run_without_fallbacks_has_no_review(isolated: Path, vault: object) -> None:
    app = tui(isolated)
    async with app.run_test(size=(120, 40)) as pilot:
        await running(pilot)
        await ready(pilot)
        await planning(pilot)
        await pilot.press("ctrl+r")
        run = await ended(pilot)

        assert not run.reviewable


async def test_a_stale_entry_says_so_and_can_only_be_accepted(
    isolated: Path, gateway: FakeGateway
) -> None:
    await fallen(isolated, gateway, "app.welcome")
    source = isolated / "locales/en/common.json"
    content = json.loads(source.read_text(encoding="utf-8"))
    del content["app"]["welcome"]
    source.write_text(json.dumps(content), encoding="utf-8")
    app = tui(isolated)
    async with app.run_test(size=(160, 45)) as pilot:
        await running(pilot)
        review = await reviewing(pilot)

        assert shown(review, "#source .text") == "no longer in the source"
        assert shown(review, "#position") == "1 of 1 · 1 stale"
        assert review.query_one("#text", Input).disabled
        assert review.check_action("edit", ()) is None
        await pilot.press("a")
        await settle(pilot)

        assert rows(review) == []
        assert not (isolated / RECORD).exists()
