from pathlib import Path

import pytest
from pydantic import ValidationError

from i18n_ai.runtime.settings import build_settings


@pytest.fixture(autouse=True)
def clean(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)
    for name in ("MODEL", "BATCH_SIZE", "CONCURRENCY", "MAX_ATTEMPTS"):
        monkeypatch.delenv(f"I18N_AI_{name}", raising=False)


def test_the_defaults() -> None:
    generation = build_settings().generation

    assert generation.model is None
    assert generation.batch_size == 40


def test_the_environment_wins_over_the_dotenv(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    (tmp_path / ".env").write_text("I18N_AI_MODEL=ollama:qwen2.5:7b\nI18N_AI_BATCH_SIZE=10\n")
    monkeypatch.setenv("I18N_AI_BATCH_SIZE", "20")

    generation = build_settings().generation

    assert generation.model == "ollama:qwen2.5:7b"
    assert generation.batch_size == 20


def test_an_invalid_setting_is_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("I18N_AI_CONCURRENCY", "many")

    with pytest.raises(ValidationError):
        build_settings()
