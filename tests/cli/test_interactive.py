"""The interactive mode, at a terminal the tests script: what a run was not told is asked, and
nothing else."""

import json
import os
import re
from collections.abc import Callable
from pathlib import Path

import keyring
import pytest
from keyring.backends import fail
from typer.testing import CliRunner

from i18n_ai.cli import interactive
from i18n_ai.cli.app import app
from i18n_ai.di import bootstrap
from support.fakes import FakeGateway, FakeModel, MemoryKeyring, ScriptedPrompter

runner = CliRunner()
ANSI = re.compile(r"\x1b\[[0-9;]*m")
KEYS = ("OPENAI_API_KEY", "ANTHROPIC_API_KEY")

Terminal = Callable[..., ScriptedPrompter]


@pytest.fixture(autouse=True)
def isolated(monkeypatch: pytest.MonkeyPatch, examples: Path, gateway: FakeGateway) -> None:
    """In the examples' copy, with no I18N_AI_* and no provider key from the developer's
    machine, the fake model, and room for rich's tables."""
    monkeypatch.chdir(examples)
    for name in ("MODEL", "BATCH_SIZE", "CONCURRENCY", "MAX_ATTEMPTS"):
        monkeypatch.delenv(f"I18N_AI_{name}", raising=False)
    for key in KEYS:
        # set first, so that what the run sets is undone too
        monkeypatch.setenv(key, "")
        monkeypatch.delenv(key)
    monkeypatch.setenv("COLUMNS", "200")


@pytest.fixture
def gateway(monkeypatch: pytest.MonkeyPatch) -> FakeGateway:
    fake = FakeGateway()
    build = bootstrap.build_container
    monkeypatch.setattr(
        bootstrap,
        "build_container",
        lambda mediator, console, *overrides: build(mediator, console, *overrides, FakeModel(fake)),
    )
    return fake


@pytest.fixture
def terminal(monkeypatch: pytest.MonkeyPatch) -> Terminal:
    """A terminal answering from a script: `terminal("i18next/locales", ["de"], ...)`."""
    monkeypatch.setattr(interactive, "is_interactive", lambda no_input: not no_input)

    def script(*answers: object) -> ScriptedPrompter:
        prompter = ScriptedPrompter(*answers)
        monkeypatch.setattr(interactive, "prompter", lambda: prompter)
        return prompter

    return script


def invoke(*args: str) -> tuple[int, str]:
    result = runner.invoke(app, list(args))
    return result.exit_code, ANSI.sub("", result.output)


def test_i18n_ai_alone_walks_every_step(
    terminal: Terminal, examples: Path, vault: MemoryKeyring
) -> None:
    prompter = terminal(
        "i18next/locales", ["fr", "de"], "", "openai", "sk-test", False, "fake-model", True
    )

    code, output = invoke()

    assert code == 0, output
    asked = [(question.kind, question.message) for question in prompter.asked]
    assert asked == [
        ("select", "Which locale tree?"),
        ("checkbox", "Which locales to generate?"),
        ("select", "Where do the new locales go?"),
        ("select", "Which provider?"),
        ("secret", "OPENAI_API_KEY (hidden)"),
        ("confirm", "Save it in the system keyring for the next runs?"),
        ("select", "Which openai model?"),
        ("confirm", "Translate 2 file(s) into fr, de (4 agent(s), 47 message(s))?"),
    ]
    trees, targets, _, providers, _, save, models, _ = prompter.asked
    assert trees.choices[:5] == [
        "bundle/i18n.json",
        "django/locale",
        "gnu/po",
        "i18next/locales",
        "icu/messages",
    ]
    assert targets.default == {"fr"}  # in the tree already
    assert "en" not in targets.choices
    assert providers.choices[0] == "anthropic"  # installed, in the tests
    assert models.choices == ["gpt-4.1-mini", "fake-model", "old-model", "\0other"]
    assert save.default is False
    assert "OPENAI_API_KEY" not in os.environ  # used for the run, and gone
    assert vault.passwords == {}
    german = json.loads((examples / "i18next/locales/de/common.json").read_text(encoding="utf-8"))
    assert german["app"]["welcome"] == "[de] Welcome back, {{name}}!"
    assert "To run it again: i18n-ai generate i18next/locales -t fr,de -m openai:fake-model" in (
        output
    )


def test_a_given_flag_is_not_asked_for(
    terminal: Terminal, examples: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    prompter = terminal(True)

    code, output = invoke("generate", "i18next/locales/en", "-t", "de", "-m", "openai:fake-model")

    assert code == 0, output
    assert [question.kind for question in prompter.asked] == ["confirm"]
    assert "To run it again" not in output


def test_the_settings_model_is_not_asked_for(
    terminal: Terminal, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("I18N_AI_MODEL", "openai:fake-model")
    prompter = terminal("sk-test", False)

    code, output = invoke("generate", "icu/messages", "-t", "de", "-o", "out", "-y")

    assert code == 0, output
    assert [question.kind for question in prompter.asked] == ["secret", "confirm"]
    assert (Path("out") / "de.json").is_file()


def test_the_source_is_asked_when_the_tree_cannot_tell(
    terminal: Terminal, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    for locale in ("fr", "de"):
        (tmp_path / "site/locales" / locale).mkdir(parents=True)
        (tmp_path / "site/locales" / locale / "app.json").write_text('{"hello": "Bonjour"}')
    monkeypatch.chdir(tmp_path / "site")
    prompter = terminal("fr — French", True)

    code, output = invoke("generate", "locales", "-t", "es", "-m", "openai:fake-model")

    assert code == 0, output
    assert prompter.asked[0].choices == ["de", "fr"]
    assert (tmp_path / "site/locales/es/app.json").is_file()
    assert "i18n-ai generate locales -t es -s fr -m openai:fake-model" in output


def test_the_last_answers_are_the_defaults(terminal: Terminal, vault: MemoryKeyring) -> None:
    terminal(
        "i18next/locales", ["de"], "Another directory…", "out", "openai", "sk", True, "old-model", 1
    )
    code, output = invoke("generate")
    assert code == 0, output
    assert "OPENAI_API_KEY saved in the system keyring" in output
    assert vault.passwords == {("i18n-ai", "OPENAI_API_KEY"): "sk"}

    prompter = terminal("bundle/i18n.json", ["fr"], "", "openai", "fake-model", False)  # no key
    code, _ = invoke("generate")

    assert code == 1  # declined
    tree, targets, output_, provider, model, _ = prompter.asked
    assert tree.default == "i18next/locales"
    assert targets.default == {"de", "es"}  # the last answer, and the bundle's own
    assert output_.default == "out"
    assert output_.choices[0] == "out"
    assert provider.default == "openai"
    assert model.default == "old-model"


def test_a_path_and_a_model_can_be_typed(terminal: Terminal) -> None:
    prompter = terminal(
        "Another path…", "icu/messages", ["ja"], "", "anthropic", "", "Another model…", "x-1", 1
    )

    code, output = invoke("generate")

    assert code == 0, output
    assert "FAKE_API_KEY is not set; showing the recommended models" in output
    assert "No ANTHROPIC_API_KEY" in output
    assert prompter.asked[6].choices == ["anthropic-pick", "\0other"]
    assert "-m anthropic:x-1" in output


def test_a_project_without_a_tree_asks_for_its_path(
    terminal: Terminal, tmp_path: Path, examples: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "empty").mkdir()
    monkeypatch.chdir(tmp_path / "empty")
    prompter = terminal(str(examples / "icu/messages"), ["ar — Arabic (rtl)"], "")

    code, output = invoke("generate", "--dry-run")

    assert code == 0, output
    assert "No locale tree found" in output
    assert [question.kind for question in prompter.asked] == ["text", "checkbox", "select"]
    assert "Arabic" in output


def test_no_input_asks_nothing(terminal: Terminal) -> None:
    prompter = terminal()

    code, output = invoke("generate", "--no-input")

    assert code == 2
    assert "Missing argument 'PATH'" in output
    assert prompter.asked == []


def test_i18n_ai_alone_shows_the_help_off_a_terminal() -> None:
    code, output = invoke()

    assert code == 0
    assert "Usage" in output
    assert "generate" in output


def test_providers_models(monkeypatch: pytest.MonkeyPatch) -> None:
    code, output = invoke("providers", "models", "openai")

    assert code == 0, output
    rows = [line for line in output.splitlines() if "-model" in line or "gpt" in line]
    assert "gpt-4.1-mini" in rows[0]
    assert "recommended" in rows[0]
    assert "fake-model" in rows[1]  # the newest after the recommended
    assert "2023-11-14" in rows[1]


def test_providers_models_fails_without_the_list() -> None:
    code, output = invoke("providers", "models", "anthropic")

    assert code == 2
    assert "error: cannot list the anthropic models: FAKE_API_KEY is not set" in output
    assert "anthropic-pick" in output


def test_providers_list_shows_the_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")

    code, output = invoke("providers", "list")

    assert code == 0
    assert "✓ OPENAI_API_KEY" in output
    assert "ANTHROPIC_API_KEY" in output


def test_a_key_that_cannot_be_saved_is_used_for_the_run(
    terminal: Terminal, monkeypatch: pytest.MonkeyPatch
) -> None:
    keyring.set_keyring(fail.Keyring())
    monkeypatch.setenv("I18N_AI_MODEL", "openai:fake-model")
    terminal("sk-test", True)

    code, output = invoke("generate", "icu/messages", "-t", "de", "-o", "out", "-y")

    assert code == 0, output
    assert "no system keyring is available" in output
    assert "OPENAI_API_KEY is used for this run only" in output
    assert (Path("out") / "de.json").is_file()


def test_the_presets_tree_is_the_first_choice(
    terminal: Terminal, examples: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(examples / "angular")
    prompter = terminal("src/locale", ["de"], "")

    code, output = invoke("generate", "--dry-run", "--preset", "angular")

    assert code == 0, output
    assert "Preset angular · --preset → src/locale (from angular.json)" in output
    tree = prompter.asked[0]
    assert tree.choices == ["src/locale", "\0other"]
    assert tree.default == "src/locale"
    assert "messages.de.xlf" in output


def test_another_tree_than_the_presets_is_read_in_its_own_format(
    terminal: Terminal, examples: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(examples / "rails")
    (examples / "rails/config/locales/en.json").write_text('{"hello": "Hello"}')
    (examples / "rails/web/locales").mkdir(parents=True)
    (examples / "rails/web/locales/en.json").write_text('{"hello": "Hello"}')
    prompter = terminal("web/locales", ["de"], "")

    code, output = invoke("generate", "--dry-run")

    assert code == 0, output
    assert prompter.asked[0].choices[:2] == ["config/locales", "web/locales"]
    assert "Format    json" in output
