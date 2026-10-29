from pathlib import Path

from rich.console import Console

from i18n_ai.application.exports.locale import (
    FileDropped,
    FileResult,
    JobDone,
    JobStarted,
    ResultStatus,
    RunFinished,
    RunStarted,
)
from i18n_ai.infra.adapters.console import RichGenerationProgress


def done(file: str, status: ResultStatus) -> JobDone:
    return JobDone(FileResult(file, "fr", Path(file), status))


def test_the_console_shows_each_file_dropped_and_each_job_done() -> None:
    console = Console(record=True, width=100, color_system=None)
    progress = RichGenerationProgress(console)

    progress.on(RunStarted(3))
    progress.on(FileDropped("meta.json", 1, "it looks like data"))
    progress.on(JobStarted("common.json", "fr"))
    progress.on(done("common.json", ResultStatus.WRITTEN))
    progress.on(done("auth/login.json", ResultStatus.PARTIAL))
    progress.on(RunFinished())

    assert console.export_text().strip("\n").splitlines() == [
        "  ⊘ ignored meta.json: it looks like data",
        "  ● common.json → fr: written",
        "  ● auth/login.json → fr: partial",
    ]
