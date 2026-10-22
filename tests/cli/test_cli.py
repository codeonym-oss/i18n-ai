"""The real `i18n-ai` commands, end to end."""

import sys
from importlib.metadata import version
from pathlib import Path

import pytest
from typer.testing import CliRunner

from i18n_ai.cli.app import app, main

runner = CliRunner()


@pytest.fixture(autouse=True)
def isolated(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """No .env and no I18N_AI_* from the developer's machine, and room for rich's tables."""
    monkeypatch.chdir(tmp_path)
    for name in ("MODEL", "BATCH_SIZE", "CONCURRENCY", "MAX_ATTEMPTS"):
        monkeypatch.delenv(f"I18N_AI_{name}", raising=False)
    monkeypatch.setenv("COLUMNS", "200")


def invoke(*args: str, answers: str | None = None) -> tuple[int, str]:
    result = runner.invoke(app, list(args), input=answers)
    return result.exit_code, result.output


def test_version() -> None:
    code, output = invoke("--version")

    assert code == 0
    assert output.strip() == f"i18n-ai {version('i18n-ai')}"


def test_main_runs_the_app(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(sys, "argv", ["i18n-ai", "--version"])

    with pytest.raises(SystemExit) as exit_:
        main()

    assert exit_.value.code == 0
    assert capsys.readouterr().out.startswith("i18n-ai ")


@pytest.mark.parametrize(
    ("tree", "layout", "file"),
    [
        ("i18next/locales/en", "directory", "auth/login.json"),
        ("icu/messages", "file", "en.json"),
        ("bundle/i18n.json", "bundle", "i18n.json"),
    ],
)
def test_scan_shows_the_tree_and_the_plan(
    examples: Path, tree: str, layout: str, file: str
) -> None:
    code, output = invoke("scan", str(examples / tree), "-t", "fr,ar")

    assert code == 0
    assert layout in output
    assert file in output
    assert "Arabic" in output
    assert "rtl" in output


def test_scan_tells_which_files_qualify(examples: Path) -> None:
    code, output = invoke("scan", str(examples / "i18next/locales/en"), "-t", "fr")

    assert code == 0
    assert "meta.json" in output
    assert "fill" in output  # fr exists, and keeps its good translations


def test_a_missing_tree_is_refused_in_one_line(tmp_path: Path) -> None:
    code, output = invoke("scan", str(tmp_path / "nowhere"))

    assert code == 2
    assert "error:" in output
    assert "it does not exist" in output
    assert "Traceback" not in output


def test_the_source_is_not_a_target(examples: Path) -> None:
    code, output = invoke("scan", str(examples / "i18next/locales/en"), "-t", "fr,EN")

    assert code == 2
    assert "error: EN is the source locale" in output


def test_an_unknown_source_is_refused(examples: Path) -> None:
    code, output = invoke("scan", str(examples / "i18next/locales"), "-s", "de")

    assert code == 2
    assert "has no de locale" in output
