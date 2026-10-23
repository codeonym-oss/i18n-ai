import shutil
from collections.abc import Iterator
from pathlib import Path

import keyring
import pytest

from support.fakes import MemoryKeyring

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


@pytest.fixture(autouse=True)
def vault() -> Iterator[MemoryKeyring]:
    """A keyring in memory in place of the system's, which no test touches."""
    system = keyring.get_keyring()
    memory = MemoryKeyring()
    keyring.set_keyring(memory)
    yield memory
    keyring.set_keyring(system)
