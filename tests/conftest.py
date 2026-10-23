import shutil
from pathlib import Path

import pytest

EXAMPLES = Path(__file__).parent.parent / "examples"


@pytest.fixture
def examples(tmp_path: Path) -> Path:
    """A copy of the examples, to write into."""
    target = tmp_path / "examples"
    shutil.copytree(EXAMPLES, target)
    return target


@pytest.fixture(autouse=True)
def state(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    """The interactive mode's remembered answers, kept out of the developer's own."""
    directory = tmp_path / "state"
    monkeypatch.setenv("I18N_AI_STATE_DIR", str(directory))
    return directory
