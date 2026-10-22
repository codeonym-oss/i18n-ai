"""The provider intents: listing the providers, and installing one."""

from ..intents import provider
from ..intents.provider import *  # noqa: F403
from . import public

__all__ = public(provider)
