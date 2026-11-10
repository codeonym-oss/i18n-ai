import dataclasses
from dataclasses import dataclass, field
from pathlib import Path

from mediary import Mediator
from rich.console import Console

from ...application.exports.locale import DetectLocaleTreesQuery
from ...application.ports.locale import TreeRequest
from ...domain.exports.locale import LocaleCode
from ...runtime.answers import Answers
from ..common import tree_request, with_preset
from ..common.setup import Choice, Shown, tree_choices, within


@dataclass(frozen=True)
class Trees:
    """The project's locale trees, as the setup lists them, the default first picked; `preset`
    is the request with the project's preset, and `preset_name` its name."""

    choices: tuple[Choice, ...] = ()
    default: str | None = None
    preset: TreeRequest = field(default_factory=lambda: TreeRequest(Path()))
    preset_name: str | None = None

    def request(self, tree: str, shown: Shown, last: Answers) -> TreeRequest:
        """The request for `tree`: with the preset's format and syntax when it is the preset's
        own, and the source and output picked for it last time."""
        base = self.preset if tree == shown(self.preset.path) else TreeRequest(Path())
        request = dataclasses.replace(base, path=Path(tree), source=None)
        if tree == last.tree:
            source = LocaleCode(last.source) if last.source else None
            output = Path(last.output) if last.output else None
            request = dataclasses.replace(request, source=source, output=output)
        return request


async def find_trees(mediator: Mediator, quiet: Console, project: Path, last: Answers) -> Trees:
    """The project's preset and trees, its preset's first."""
    base = tree_request(Path(), None, None, None, None)
    preset, match = await with_preset(mediator, quiet, base, None, given=False)
    candidates = await mediator.send(DetectLocaleTreesQuery(project))
    choices, default = tree_choices(candidates, match, last, within(project))
    name = match.preset.name if match is not None else None
    return Trees(tuple(choices), default, preset, name)
