"""The presets: what each i18n library reveals itself by in a project, where its locales are,
and how they are written. They are plain data, so a new library is a new row of `PRESETS`."""

from ..exceptions import PresetUnknown
from .preset import ConfigHint, Preset
from .table import PRESETS


def preset_named(name: str) -> Preset:
    """The preset called `name`, whatever its case. Raises `PresetUnknown`."""
    wanted = name.strip().lower()
    for preset in PRESETS:
        if preset.name == wanted:
            return preset
    raise PresetUnknown(name, [preset.name for preset in PRESETS])


__all__ = ["PRESETS", "ConfigHint", "Preset", "preset_named"]
