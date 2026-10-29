from rich.console import Console
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TaskID,
    TextColumn,
    TimeElapsedColumn,
)

from ....application.exports.locale import (
    FileDropped,
    FileResult,
    JobDone,
    ProgressEvent,
    RunFinished,
    RunStarted,
)
from ....application.ports.progress import IGenerationProgress

_STATUS_STYLE = {"written": "green", "partial": "yellow", "refused": "red", "failed": "red"}


class RichGenerationProgress(IGenerationProgress):
    """A progress bar of the jobs, with a line for each one done."""

    def __init__(self, console: Console) -> None:
        self._console = console
        self._progress: Progress | None = None
        self._task: TaskID | None = None
        self._total = 0

    def on(self, event: ProgressEvent) -> None:
        match event:
            case RunStarted(jobs):
                self._start(jobs)
            case FileDropped(file, jobs, reason):
                self._drop(jobs, f"{file}: {reason}")
            case JobDone(result):
                self._done(result)
            case RunFinished():
                self._finish()
            case _:
                pass  # the atoms' starts and retries are not shown here

    def _start(self, jobs: int) -> None:
        self._total = jobs
        self._progress = Progress(
            SpinnerColumn(),
            TextColumn("[bold]{task.description}"),
            BarColumn(),
            MofNCompleteColumn(),
            TimeElapsedColumn(),
            console=self._console,
            transient=True,
        )
        self._progress.start()
        self._task = self._progress.add_task("Translating", total=jobs)

    def _drop(self, jobs: int, reason: str) -> None:
        self._total = max(0, self._total - jobs)
        if self._progress is not None and self._task is not None:
            self._progress.update(self._task, total=self._total)
        self._console.print(f"  [dim]⊘ ignored {reason}[/]")

    def _done(self, result: FileResult) -> None:
        style = _STATUS_STYLE.get(result.status.value, "white")
        self._console.print(
            f"  [{style}]●[/] {result.file} → {result.target}: {result.status.value}"
        )
        if self._progress is not None and self._task is not None:
            self._progress.advance(self._task)

    def _finish(self) -> None:
        if self._progress is not None:
            self._progress.stop()
            self._progress = None
