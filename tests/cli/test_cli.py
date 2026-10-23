"""The real `i18n-ai` commands, end to end: the container gets the fake model in place of the
provider's, and nothing reaches a network or installs a package."""

import json
import re
import sys
from importlib.metadata import version
from pathlib import Path

import pytest
from typer.testing import CliRunner

from i18n_ai.cli.app import app, main
from i18n_ai.di import bootstrap
from support.fakes import FakeGateway, FakeModel

runner = CliRunner()
# Typer forces colors on CI (GITHUB_ACTIONS, FORCE_COLOR): the tests read the text alone.
ANSI = re.compile(r"\x1b\[[0-9;]*m")


@pytest.fixture(autouse=True)
def isolated(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """No .env and no I18N_AI_* from the developer's machine, and room for rich's tables."""
    monkeypatch.chdir(tmp_path)
    for name in ("MODEL", "BATCH_SIZE", "CONCURRENCY", "MAX_ATTEMPTS"):
        monkeypatch.delenv(f"I18N_AI_{name}", raising=False)
    monkeypatch.setenv("COLUMNS", "200")


@pytest.fixture
def gateway(monkeypatch: pytest.MonkeyPatch) -> FakeGateway:
    """The fake model, put in the container every command builds."""
    fake = FakeGateway()
    build = bootstrap.build_container
    monkeypatch.setattr(
        bootstrap,
        "build_container",
        lambda mediator, console, *overrides: build(mediator, console, *overrides, FakeModel(fake)),
    )
    return fake


def invoke(*args: str, answers: str | None = None) -> tuple[int, str]:
    result = runner.invoke(app, list(args), input=answers)
    return result.exit_code, ANSI.sub("", result.output)


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
        ("rails/config/locales", "file", "en.yml"),
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


def test_scan_tells_the_format(examples: Path) -> None:
    (examples / "i18next/locales/en/extra.yml").write_text("a: A\n")

    code, output = invoke("scan", str(examples / "i18next/locales/en"))
    assert code == 2
    # the temporary directory's long path may wrap the line
    assert "mixes the formats json, yaml; choose the one to translate with --format" in " ".join(
        output.split()
    )

    code, output = invoke("scan", str(examples / "i18next/locales/en"), "--format", "YAML")
    assert code == 0, output
    assert "Format    yaml" in output
    assert "extra.yml" in output
    assert "common.json" not in output


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


def test_generate_needs_a_target(examples: Path) -> None:
    code, output = invoke("generate", str(examples / "i18next/locales/en"))

    assert code == 2
    assert "Missing option '--target'" in output

    code, output = invoke("generate", str(examples / "i18next/locales/en"), "-t", ",")

    assert code == 2
    assert "at least one target" in output


def test_the_source_is_not_a_target(examples: Path) -> None:
    code, output = invoke("scan", str(examples / "i18next/locales/en"), "-t", "fr,EN")

    assert code == 2
    assert "error: EN is the source locale" in output


def test_an_unknown_source_is_refused(examples: Path) -> None:
    code, output = invoke("scan", str(examples / "i18next/locales"), "-s", "de")

    assert code == 2
    assert "has no de locale" in output


def test_a_dry_run_stops_after_the_precheck(examples: Path, gateway: FakeGateway) -> None:
    locales = examples / "i18next/locales"

    code, output = invoke("generate", str(locales / "en"), "-t", "de", "--dry-run")

    assert code == 0
    assert "common.json" in output
    assert not (locales / "de").exists()
    assert gateway.batches == []


def test_generate_needs_a_model(examples: Path) -> None:
    code, output = invoke("generate", str(examples / "i18next/locales/en"), "-t", "de", "-y")

    assert code == 2
    assert "--model" in output


def test_generate_writes_the_targets(examples: Path, gateway: FakeGateway) -> None:
    locales = examples / "i18next/locales"

    code, output = invoke(
        "generate", str(locales / "en"), "-t", "de,ar", "-m", "openai:fake-model", "-y"
    )

    assert code == 0, output
    assert "Generated with openai:fake-model" in output
    german = json.loads((locales / "de/common.json").read_text(encoding="utf-8"))
    assert german["app"]["welcome"] == "[de] Welcome back, {{name}}!"
    assert (locales / "ar/auth/login.json").is_file()
    assert not (locales / "de/meta.json").exists()


def test_declining_writes_nothing(examples: Path, gateway: FakeGateway) -> None:
    locales = examples / "i18next/locales"

    code, _ = invoke(
        "generate", str(locales / "en"), "-t", "de", "-m", "openai:fake-model", answers="n\n"
    )

    assert code == 1
    assert not (locales / "de").exists()
    assert gateway.batches == []


def test_a_strict_run_refuses_a_file_with_failures(
    examples: Path, gateway: FakeGateway, monkeypatch: pytest.MonkeyPatch
) -> None:
    gateway.broken_first = {"app.welcome"}
    locales = examples / "i18next/locales"

    code, output = invoke(
        "generate",
        str(locales / "en"),
        "-t",
        "de",
        "-m",
        "openai:fake-model",
        "--include",
        "common.json",
        "--max-attempts",
        "1",
        "--strict",
        "-y",
    )

    assert code == 1
    assert "refused" in output
    assert not (locales / "de/common.json").exists()


def test_providers_list() -> None:
    code, output = invoke("providers", "list")

    assert code == 0
    assert "openai" in output
    assert "langchain-openai" in output


def test_providers_check(gateway: FakeGateway) -> None:
    code, output = invoke("providers", "check", "anthropic:claude-sonnet-4-5")

    assert code == 0
    assert "langchain-anthropic" in output


def test_an_unknown_provider_is_refused() -> None:
    code, output = invoke("providers", "check", "nobody:some-model")

    assert code == 2
    assert "nobody" in output


def flat(output: str) -> str:
    """The output on one line, as the temporary directory's long paths may wrap it."""
    return " ".join(output.split())


def test_scan_with_no_path_uses_the_projects_preset(
    examples: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(examples / "flutter")

    code, output = invoke("scan", "-t", "fr")

    assert code == 0, output
    assert "Preset flutter · flutter_localizations in pubspec.yaml → lib/l10n" in output
    assert "(from l10n.yaml)" in output
    assert "Format    arb" in output
    assert "app_fr.arb" in output


def test_a_named_preset_overrides_the_detected_one(
    examples: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (examples / "i18next/locales/en/extra.yml").write_text("a: A\n")
    monkeypatch.chdir(examples / "i18next")

    code, output = invoke("scan", "locales/en", "--preset", "rails")

    assert code == 0, output
    assert "Preset rails · --preset" in output
    assert "Format    yaml" in output  # the preset's
    assert "extra.yml" in output

    code, output = invoke("scan", "--preset", "nope")

    assert code == 2
    assert "no preset is called nope" in flat(output)


def test_scan_with_no_path_and_no_preset_takes_the_only_tree(
    examples: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(examples / "symfony")

    code, output = invoke("scan")

    assert code == 0, output
    assert "Preset" not in output
    assert "Locale tree: translations" in output

    monkeypatch.chdir(examples)
    code, output = invoke("scan")

    assert code == 2
    assert "it has no preset's locales and no single locale tree" in flat(output)


def test_presets_lists_them_and_the_one_used_here(
    examples: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(examples / "rails")

    code, output = invoke("presets")

    assert code == 0
    assert "rails ●" in output
    assert "config/locales/<lng>.yml" in output
    assert "Here: Preset rails · rails in Gemfile → config/locales" in output

    monkeypatch.chdir(examples / "bundle")
    code, output = invoke("presets")

    assert code == 0
    assert "●" not in output
    assert "No i18n library is detected here." in output


def test_generate_with_no_path_uses_the_projects_preset(
    examples: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (examples / "icu/messages/notes.yml").write_text("a: A\n")  # not next-intl's format
    monkeypatch.chdir(examples / "icu")

    code, output = invoke("generate", "-t", "de", "--dry-run", "--no-input")

    assert code == 0, output
    assert "Preset next-intl · next-intl in package.json → messages" in output
    assert "de.json" in output

    code, output = invoke("generate", "--dry-run", "--no-input")

    assert code == 2
    assert "Missing option '--target'" in output
