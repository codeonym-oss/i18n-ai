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
