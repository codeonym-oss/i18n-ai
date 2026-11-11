"""The setup as Aurora's wizard: its three steps, the locale cards, the model card and the
run's panel, on the i18next example (en → fr, fr 3 of 26 messages done, 24 in the source)."""

from pathlib import Path

import pytest
from textual.pilot import Pilot
from textual.widgets import ContentSwitcher, Input, Static

from i18n_ai.cli.tui.kit.widgets import LocaleCard, ModelCard
from support.tui import pick, pick_targets, running, settle, tui


def step(pilot: Pilot[None]) -> str:
    return str(pilot.app.screen.query_one("#wizard", ContentSwitcher).current)


def cards(pilot: Pilot[None]) -> list[LocaleCard]:
    return list(pilot.app.screen.query(LocaleCard))


def figures(pilot: Pilot[None]) -> dict[str, str]:
    screen = pilot.app.screen
    return {
        name: str(screen.query_one(f"#{name} .figure-value", Static).content)
        for name in ("files", "locales", "messages")
    }


def said(pilot: Pilot[None], text: str) -> bool:
    return any(text in str(notification.message) for notification in pilot.app._notifications)


async def test_it_opens_on_targets_with_the_trees_locale_picked(isolated: Path) -> None:
    app = tui(isolated)
    async with app.run_test(size=(160, 45)) as pilot:
        await running(pilot)
        screen = app.screen

        assert step(pilot) == "targets-step"
        assert str(screen.query_one("#crumb", Static).content) == "New run / Targets"
        assert str(screen.query_one("#status-tree", Static).content).startswith(
            "step 2 of 3 · targets"
        )
        french, spanish = cards(pilot)[:2]
        assert (french.code, french.direction, french.locale_name) == ("fr", "LTR", "French")
        assert french.state == "in tree · 11% done"
        assert french.picked
        assert (spanish.code, spanish.state, spanish.picked) == ("es", "new · 24 messages", False)
        assert figures(pilot) == {"files": "2", "locales": "1", "messages": "23"}


async def test_a_chip_continue_and_escape_move_between_the_steps(isolated: Path) -> None:
    app = tui(isolated)
    async with app.run_test(size=(160, 45)) as pilot:
        await running(pilot)

        await pilot.click("#step-model")
        await settle(pilot)
        assert step(pilot) == "model-step"
        assert not app.screen.query_one("#continue").display

        await pilot.press("escape")
        assert step(pilot) == "targets-step"
        await pilot.press("escape")
        assert step(pilot) == "tree-step"
        await pilot.press("escape")
        assert step(pilot) == "tree-step"

        await pilot.click("#continue")
        await settle(pilot)
        assert step(pilot) == "targets-step"


async def test_plan_opens_the_step_that_misses_something(isolated: Path) -> None:
    app = tui(isolated)
    async with app.run_test(size=(160, 45)) as pilot:
        await running(pilot)
        await pick_targets(pilot, "fr")  # fr off: no target left
        await pilot.click("#step-model")
        await settle(pilot)

        await pilot.press("ctrl+r")
        await settle(pilot)

        assert step(pilot) == "targets-step"
        assert said(pilot, "Pick a target first.")


async def test_it_opens_on_tree_when_the_source_is_asked_and_stays_there(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    for locale in ("fr", "de"):
        (tmp_path / "site/locales" / locale).mkdir(parents=True)
        (tmp_path / "site/locales" / locale / "app.json").write_text('{"hello": "Bonjour"}')
    monkeypatch.chdir(tmp_path / "site")
    app = tui(tmp_path / "site")
    async with app.run_test(size=(160, 45)) as pilot:
        await running(pilot)
        await pick(pilot, "#tree", "locales")
        assert step(pilot) == "tree-step"
        assert app.screen.query_one("#source-row").display
        assert app.screen.query_one("#search", Input).disabled
        assert not cards(pilot)

        await pick(pilot, "#source", "fr")

        assert step(pilot) == "tree-step"
        assert [card.code for card in cards(pilot) if card.picked] == ["de"]


async def test_the_search_keeps_what_is_picked(isolated: Path) -> None:
    app = tui(isolated)
    async with app.run_test(size=(160, 45)) as pilot:
        await running(pilot)
        await pilot.press("slash", *"germ")
        await settle(pilot)

        assert [card.locale_name for card in cards(pilot)] == [
            "German",
            "German (Switzerland)",
            "Low German",
            "Swiss German",
        ]
        assert str(app.screen.query_one("#matches", Static).content) == "4 match"
        cards(pilot)[0].action_pick()
        await settle(pilot)

        app.screen.query_one("#search", Input).value = ""
        await settle(pilot)

        assert [card.code for card in cards(pilot) if card.picked] == ["fr", "de"]
        assert figures(pilot)["locales"] == "2"


async def test_the_filters_and_the_cap(isolated: Path) -> None:
    app = tui(isolated)
    async with app.run_test(size=(160, 45)) as pilot:
        await running(pilot)
        screen = app.screen
        assert len(cards(pilot)) == 24
        assert str(screen.query_one("#more", Static).content) == "+298 more · type to narrow"
        assert str(screen.query_one("#filter-tree", Static).content) == "In the tree · 1"

        await pilot.click("#filter-rtl")
        await settle(pilot)
        assert len(cards(pilot)) == 22
        assert {card.direction for card in cards(pilot)} == {"RTL"}
        assert not screen.query_one("#more").display

        await pilot.click("#filter-picked")
        await settle(pilot)
        assert [card.code for card in cards(pilot)] == ["fr"]


async def test_space_on_a_card_picks_it_and_the_panel_counts_it(isolated: Path) -> None:
    app = tui(isolated)
    async with app.run_test(size=(160, 45)) as pilot:
        await running(pilot)
        spanish = cards(pilot)[1]
        spanish.focus()
        await pilot.press("space")
        await settle(pilot)

        assert spanish.picked
        assert str(app.screen.query_one("#filter-picked", Static).content) == "Picked · 2"
        chips = app.screen.query("#picked .chip")
        assert [str(chip.content) for chip in chips] == ["fr ×", "es ×"]
        assert figures(pilot)["locales"] == "2"


async def test_the_model_card_says_the_keys_state(isolated: Path) -> None:
    app = tui(isolated)
    async with app.run_test(size=(160, 45)) as pilot:
        await running(pilot)
        await pick(pilot, "#provider", "openai")
        card = app.screen.query_one("#model-card", ModelCard)
        assert card.text == "openai / … · key needed"

        key = app.screen.query_one("#key", Input)
        key.value = "sk-test"
        await key.action_submit()
        await settle(pilot)
        await pick(pilot, "#model", "fake-model")

        assert card.text == "openai / fake-model · ✓ set (for this run)"
        assert app.screen.query_one("#run-model", ModelCard).text == card.text
