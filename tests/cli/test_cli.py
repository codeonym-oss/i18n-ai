"""The real `i18n-ai` commands, end to end."""

import sys
from importlib.metadata import version

import pytest
from typer.testing import CliRunner

from i18n_ai.cli.app import app, main

runner = CliRunner()


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
