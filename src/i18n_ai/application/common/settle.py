import logging

from ...domain.exports.locale import LocaleTree
from ..ports.locale import FileFailed, FileTranslated, ILocaleStore
from ..ports.progress import FileResult, ResultStatus

logger = logging.getLogger(__name__)

WRITTEN = (ResultStatus.WRITTEN, ResultStatus.PARTIAL)


async def settle(
    store: ILocaleStore, tree: LocaleTree, event: FileTranslated | FileFailed, strict: bool
) -> FileResult:
    """Write a translated file, unless it is refused; and say what became of it."""
    job = event.job
    location = tree.target_location(job.target, job.file)
    name, target = str(job.file.name), job.target.value
    if isinstance(event, FileFailed):
        logger.warning("%s → %s failed: %s", name, target, event.error)
        return FileResult(name, target, location.path, ResultStatus.FAILED, reason=event.error)

    status = ResultStatus.PARTIAL if event.failures else ResultStatus.WRITTEN
    if event.failures and strict:
        status = ResultStatus.REFUSED
    else:
        await store.write(location, event.content, job.file)
    return FileResult(
        file=name,
        target=target,
        path=location.path,
        status=status,
        translated=event.translated,
        reused=event.reused,
        failures=event.failures,
        warnings=event.warnings,
    )
