from dataclasses import dataclass

from .result import FileResult


@dataclass(frozen=True)
class RunStarted:
    """The atoms planned: each a file into a target."""

    jobs: int


@dataclass(frozen=True)
class JobStarted:
    file: str
    target: str


@dataclass(frozen=True)
class JobRetrying:
    """`messages` broke the rules and are sent back: `attempt` of `attempts` comes next."""

    file: str
    target: str
    messages: int
    attempt: int
    attempts: int


@dataclass(frozen=True)
class JobDone:
    result: FileResult


@dataclass(frozen=True)
class FileDropped:
    """A file the model says is not a locale document: its `jobs`, its atoms, are left out."""

    file: str
    jobs: int
    reason: str


@dataclass(frozen=True)
class RunFinished:
    pass


ProgressEvent = RunStarted | JobStarted | JobRetrying | JobDone | FileDropped | RunFinished
