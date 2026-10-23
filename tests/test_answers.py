from pathlib import Path

import pytest

from i18n_ai.runtime import answers as module
from i18n_ai.runtime.answers import Answers, load_answers, save_answers, state_directory


def test_the_answers_are_kept_per_project(tmp_path: Path, state: Path) -> None:
    save_answers(tmp_path / "a", Answers(tree="locales", targets=["fr"], model="openai:x"))
    save_answers(tmp_path / "b", Answers(tree="messages"))

    assert load_answers(tmp_path / "a") == Answers(tree="locales", targets=["fr"], model="openai:x")
    assert load_answers(tmp_path / "b").tree == "messages"
    assert load_answers(tmp_path / "c") == Answers()
    assert (state / "answers.json").is_file()


def test_unreadable_answers_are_ignored(tmp_path: Path, state: Path) -> None:
    state.mkdir()
    (state / "answers.json").write_text("{")
    assert load_answers(tmp_path) == Answers()

    (state / "answers.json").write_text('["not", "a", "map"]')
    assert load_answers(tmp_path) == Answers()

    (state / "answers.json").write_text(f'{{"{tmp_path.resolve()}": {{"tree": "a", "x": 2}}}}')
    assert load_answers(tmp_path) == Answers(tree="a")


def test_answers_that_cannot_be_written_are_lost_quietly(tmp_path: Path, state: Path) -> None:
    state.write_text("a file, not a directory")

    save_answers(tmp_path, Answers(tree="locales"))

    assert load_answers(tmp_path) == Answers()


@pytest.mark.parametrize(
    ("platform", "variable", "expected"),
    [
        ("linux", "XDG_STATE_HOME", "xdg/i18n-ai"),
        ("win32", "LOCALAPPDATA", "xdg/i18n-ai"),
        ("darwin", None, "Library/Application Support/i18n-ai"),
    ],
)
def test_the_state_directory_follows_the_platform(
    monkeypatch: pytest.MonkeyPatch, platform: str, variable: str | None, expected: str
) -> None:
    monkeypatch.delenv("I18N_AI_STATE_DIR")
    monkeypatch.setattr(module.sys, "platform", platform)
    monkeypatch.setattr(module.Path, "home", lambda: Path("/home/me"))
    if variable:
        monkeypatch.setenv(variable, "xdg")

    assert state_directory().as_posix().endswith(expected)
