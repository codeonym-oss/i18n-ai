from collections.abc import Iterable

from ...domain.exports.locale import LocaleCode, LocaleTree, TargetIsSource


def validated_targets(tree: LocaleTree, targets: Iterable[LocaleCode]) -> tuple[LocaleCode, ...]:
    """`targets` without repeats, in the order given. Raises `TargetIsSource`."""
    kept: list[LocaleCode] = []
    for target in targets:
        if target.same_as(tree.source):
            raise TargetIsSource(target.value)
        if not any(target.same_as(other) for other in kept):
            kept.append(target)
    return tuple(kept)
