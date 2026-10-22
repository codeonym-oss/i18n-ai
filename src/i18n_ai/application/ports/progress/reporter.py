from abc import ABC, abstractmethod


class IGenerationProgress(ABC):
    """Shows a generation as it goes: the jobs (a file into a target) planned, those dropped
    when their file does not qualify, and those done."""

    @abstractmethod
    def start(self, jobs: int) -> None:
        raise NotImplementedError

    @abstractmethod
    def drop(self, jobs: int, reason: str) -> None:
        raise NotImplementedError

    @abstractmethod
    def advance(self, description: str) -> None:
        raise NotImplementedError

    @abstractmethod
    def finish(self) -> None:
        raise NotImplementedError
