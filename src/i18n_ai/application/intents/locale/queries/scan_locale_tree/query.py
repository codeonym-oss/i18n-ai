from dataclasses import dataclass

from mediary.cqrs import Query, query

from ......domain.exports.locale import LocaleCode
from .....ports.locale import TreeRequest
from .view import ScanReport


@query
@dataclass(frozen=True)
class ScanLocaleTreeQuery(Query[ScanReport]):
    """The precheck of a generation: the tree, its source files and whether each qualifies, and
    for each target where its files go and how many messages each needs. Raises
    `LocaleTreeNotFound`, `SourceLocaleUnknown`, `MixedLocaleFormats` or `TargetIsSource`."""

    tree: TreeRequest
    targets: tuple[LocaleCode, ...] = ()
