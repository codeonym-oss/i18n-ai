import json
from pathlib import Path, PurePosixPath

from i18n_ai.application.ports.locale import FallbackProblem, RecordedFallback
from i18n_ai.domain.exports.locale import KeyPath, ViolationCode
from i18n_ai.infra.adapters.filesystem import FileSystemFallbackRecord

RECORD = ".i18n-ai-fallbacks.json"


def entry(file: str, *path: str | int, key: str | None = None) -> RecordedFallback:
    return RecordedFallback(
        PurePosixPath(file),
        key,
        KeyPath(path),
        (FallbackProblem(ViolationCode.PLACEHOLDERS, "{{name}} is missing"),),
        "Compte bloqué",
    )


async def test_a_record_reads_back_as_it_was_written(tmp_path: Path) -> None:
    entries = (
        entry("fr.json", "Welcome back. Log in."),
        entry("fr/auth.json", "steps", 2),
        entry("messages.json", "title", key="fr"),
    )
    record = FileSystemFallbackRecord()

    await record.write(tmp_path, entries)

    assert set(await record.read(tmp_path)) == set(entries)


async def test_the_record_is_sorted_and_its_paths_are_segments(tmp_path: Path) -> None:
    await FileSystemFallbackRecord().write(
        tmp_path, (entry("fr/b.json", "z"), entry("de/a.json", "steps", 2))
    )

    text = (tmp_path / RECORD).read_text(encoding="utf-8")
    assert text.endswith("}\n")
    assert json.loads(text) == {
        "version": 1,
        "fallbacks": [
            {
                "file": "de/a.json",
                "path": ["steps", 2],
                "problems": [{"rule": "placeholders", "message": "{{name}} is missing"}],
                "rejected": "Compte bloqué",
            },
            {
                "file": "fr/b.json",
                "path": ["z"],
                "problems": [{"rule": "placeholders", "message": "{{name}} is missing"}],
                "rejected": "Compte bloqué",
            },
        ],
    }


async def test_no_entries_means_no_record(tmp_path: Path) -> None:
    record = FileSystemFallbackRecord()
    await record.write(tmp_path, (entry("fr.json", "title"),))

    await record.write(tmp_path, ())

    assert not (tmp_path / RECORD).exists()
    assert await record.read(tmp_path) == ()


async def test_a_record_that_cannot_be_read_is_empty(tmp_path: Path) -> None:
    record = FileSystemFallbackRecord()
    (tmp_path / RECORD).write_text("{not json", encoding="utf-8")
    assert await record.read(tmp_path) == ()

    (tmp_path / RECORD).write_text('{"version": 2, "fallbacks": []}', encoding="utf-8")
    assert await record.read(tmp_path) == ()
