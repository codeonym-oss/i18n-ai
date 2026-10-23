import os
import tempfile
from pathlib import Path


def read_text(path: Path) -> tuple[str, str]:
    """The text of `path`, its lines ending in `\\n`, and the line ending it uses."""
    with path.open(encoding="utf-8-sig", newline="") as file:
        raw = file.read()
    return raw.replace("\r\n", "\n"), newline_of(raw)


def newline_of(text: str) -> str:
    """The line ending `text` uses: `\\r\\n` when its first line ends so, else `\\n`."""
    end = text.find("\n")
    return "\r\n" if end > 0 and text[end - 1] == "\r" else "\n"


def write_atomically(path: Path, text: str, newline: str = "\n") -> None:
    """Write `text` to `path` through a temporary file, so a reader never sees half of it, with
    its lines ending in `newline` on every platform."""
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(handle, "w", encoding="utf-8", newline=newline) as file:
            file.write(text)
        os.replace(temporary, path)
    except BaseException:
        Path(temporary).unlink(missing_ok=True)
        raise
