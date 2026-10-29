from collections import Counter
from dataclasses import dataclass

from .....ports.progress import FileResult, ResultStatus


@dataclass(frozen=True)
class GenerationReceipt:
    model: str
    results: tuple[FileResult, ...]

    def count(self) -> Counter[ResultStatus]:
        return Counter(result.status for result in self.results)

    @property
    def ok(self) -> bool:
        return not any(
            result.status in (ResultStatus.FAILED, ResultStatus.REFUSED) for result in self.results
        )
