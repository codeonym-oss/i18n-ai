from pathlib import Path

from ...application.exports.locale import DetectPresetQuery, ListPresetsQuery
from ...di import Bootstrap
from ..common import run
from ..rendering import render_presets


def presets() -> None:
    """List the presets: each i18n library, what reveals it in a project, where it keeps its
    locales, their format and placeholders; and the one this project uses."""

    async def flow(app: Bootstrap) -> int:
        listed = await app.mediator.send(ListPresetsQuery())
        render_presets(app.console, listed, await app.mediator.send(DetectPresetQuery(Path.cwd())))
        return 0

    run(flow)
