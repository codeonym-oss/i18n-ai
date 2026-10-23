"""The last answers of the interactive mode, per project, offered as defaults on the next run.
They are kept outside the project, in i18n-ai's state directory (`I18N_AI_STATE_DIR`, else the
platform's: `~/.local/state/i18n-ai`, `~/Library/Application Support/i18n-ai`,
`%LOCALAPPDATA%\\i18n-ai`), keyed by the project's directory. Losing them costs nothing, so a
file that cannot be read or written is ignored."""

import json
import logging
import os
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class Answers:
    tree: str | None = None
    source: str | None = None
    targets: list[str] = field(default_factory=list)
    output: str | None = None
    model: str | None = None


def state_directory() -> Path:
    if configured := os.environ.get("I18N_AI_STATE_DIR"):
        return Path(configured)
    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA") or Path.home() / "AppData" / "Local"
        return Path(base) / "i18n-ai"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "i18n-ai"
    base = os.environ.get("XDG_STATE_HOME") or Path.home() / ".local" / "state"
    return Path(base) / "i18n-ai"


def _file() -> Path:
    return state_directory() / "answers.json"


def _read() -> dict[str, dict[str, object]]:
    try:
        content = json.loads(_file().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return content if isinstance(content, dict) else {}


def load_answers(project: Path) -> Answers:
    saved = _read().get(str(project.resolve()))
    if not isinstance(saved, dict):
        return Answers()
    known = {name: value for name, value in saved.items() if name in Answers.__dataclass_fields__}
    try:
        return Answers(**known)  # type: ignore[arg-type]
    except TypeError:
        return Answers()


def save_answers(project: Path, answers: Answers) -> None:
    content = _read()
    content[str(project.resolve())] = asdict(answers)
    try:
        _file().parent.mkdir(parents=True, exist_ok=True)
        _file().write_text(json.dumps(content, indent=2) + "\n", encoding="utf-8")
    except OSError:
        logger.debug("Cannot remember the answers in %s", _file(), exc_info=True)
