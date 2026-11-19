"""The TUI, driven with Textual's pilot in a copy of the examples, with the fake model."""

from pathlib import Path

import pytest
from textual.widgets import ContentSwitcher, Input, Select, Static
from textual.widgets.select import InvalidSelectValueError

from i18n_ai.cli.tui.confirm import ConfirmScreen
from i18n_ai.cli.tui.kit.widgets import LocaleCard
from i18n_ai.cli.tui.setup import SetupScreen
from support.fakes import InstalledCatalog
from support.tui import pick, running, settle, tui


async def test_the_setup_starts_from_the_projects_preset(isolated: Path) -> None:
    app = tui(isolated)
    async with app.run_test(size=(100, 40)) as pilot:
        await running(pilot)
        screen = app.screen

        assert isinstance(screen, SetupScreen)
        assert app.sub_title == "i18next preset"
        assert screen.query_one("#tree", Select).value == "locales"
        assert [card.code for card in screen.query(LocaleCard) if card.picked] == ["fr"]
        assert not screen.query_one("#source-row").display
        assert str(screen.query_one("#files .figure-value", Static).content) == "2"
        assert str(screen.query_one("#locales .figure-value", Static).content) == "1"


async def test_the_model_waits_for_its_provider_and_a_missing_key_is_asked(
    isolated: Path,
) -> None:
    app = tui(isolated)
    async with app.run_test(size=(100, 40)) as pilot:
        await running(pilot)
        screen = app.screen
        assert screen.query_one("#model", Select).disabled

        await pick(pilot, "#provider", "openai")

        assert not screen.query_one("#model", Select).disabled
        assert screen.query_one("#model", Select).is_blank()
        assert screen.query_one("#key", Input).display
        assert screen.query_one("#key", Input).password


async def test_declining_the_install_goes_back_to_the_setup(
    isolated: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(InstalledCatalog, "is_installed", lambda self, module: False)
    app = tui(isolated)
    async with app.run_test(size=(100, 40)) as pilot:
        await running(pilot)
        await pick(pilot, "#provider", "ollama")
        await pick(pilot, "#model", "ollama-pick")

        await pilot.press("ctrl+r")
        await pilot.pause(0.2)
        assert isinstance(app.screen, ConfirmScreen)
        assert "needs langchain-ollama" in str(app.screen.question)
        await pilot.press("n")
        await settle(pilot)

        assert isinstance(app.screen, SetupScreen)
        assert not (isolated / "locales/de").exists()


async def test_the_settings_model_is_the_default(isolated: Path) -> None:
    app = tui(isolated, model="openai:old-model")
    async with app.run_test(size=(100, 40)) as pilot:
        await running(pilot)

        assert app.screen.query_one("#provider", Select).value == "openai"
        assert app.screen.query_one("#model", Select).value == "old-model"


async def test_another_provider_clears_the_models(isolated: Path) -> None:
    app = tui(isolated, model="openai:old-model")
    async with app.run_test(size=(100, 40)) as pilot:
        await running(pilot)

        await pick(pilot, "#provider", "ollama")

        models = app.screen.query_one("#model", Select)
        assert models.is_blank()
        with pytest.raises(InvalidSelectValueError):
            models.value = "old-model"
        models.value = "ollama-pick"


async def test_with_no_tree_found_its_path_is_typed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    project = tmp_path / "project"
    # out/ is left out of the search
    (project / "out/i18n/en").mkdir(parents=True)
    (project / "out/i18n/en/app.json").write_text('{"hello": "Hello"}')
    monkeypatch.chdir(project)
    app = tui(project)
    async with app.run_test(size=(100, 40)) as pilot:
        await running(pilot)
        screen = app.screen
        assert not screen.query_one("#tree", Select).display
        assert screen.query_one("#wizard", ContentSwitcher).current == "tree-step"
        path = screen.query_one("#tree-path", Input)
        assert path.display

        path.value = "out/i18n"
        await path.action_submit()
        await settle(pilot)

        assert not screen.query_one("#search", Input).disabled
        assert screen.query(LocaleCard)


async def test_run_waits_for_the_setup(isolated: Path) -> None:
    app = tui(isolated)
    async with app.run_test(size=(100, 40)) as pilot:
        await running(pilot)

        await pilot.press("ctrl+r")
        await settle(pilot)

        assert isinstance(app.screen, SetupScreen)
        assert app.screen.query_one("#wizard", ContentSwitcher).current == "model-step"
        assert any("Pick a model first." in str(n.message) for n in app._notifications)


async def test_the_palette_quits(isolated: Path) -> None:
    app = tui(isolated)
    async with app.run_test(size=(100, 40)) as pilot:
        await running(pilot)

        await pilot.press("ctrl+p")
        await pilot.press(*"quit")
        await pilot.pause(0.3)
        await pilot.press("enter")
        await pilot.pause(0.3)

        assert not app.is_running


async def test_every_field_fits_80_columns(isolated: Path) -> None:
    app = tui(isolated)
    async with app.run_test(size=(80, 24)) as pilot:
        await running(pilot)
        await pick(pilot, "#provider", "openai")
        screen = app.screen
        steps: dict[str, tuple[str | type[LocaleCard], ...]] = {
            "tree": ("#tree", "#output"),
            "targets": ("#search", "#filter-picked", LocaleCard),
            "model": ("#provider", "#model", "#key"),
        }

        for step, selectors in steps.items():
            await pilot.click(f"#step-{step}")
            await settle(pilot)
            for selector in (*selectors, "#next"):
                field = screen.query_one(selector)
                field.scroll_visible(animate=False)
                await pilot.pause()
                assert field.region.width > 0, (step, selector)
                assert field.region.right <= 80, (step, selector)
                assert 0 < field.region.bottom <= 24, (step, selector)
