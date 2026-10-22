"""The locale intents: scanning a tree, and generating its targets."""

from ..intents import locale
from ..intents.locale import *  # noqa: F403
from . import public

__all__ = public(locale)
