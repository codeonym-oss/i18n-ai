from abc import ABC, abstractmethod

from .events import ProgressEvent


class IGenerationProgress(ABC):
    """Shows a generation as it goes, one event at a time: the jobs (a file into a target)
    planned, each started, retried and done, the files dropped when they do not qualify, and the
    end."""

    @abstractmethod
    def on(self, event: ProgressEvent) -> None:
        raise NotImplementedError
