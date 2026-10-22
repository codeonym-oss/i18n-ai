import logging

from mediary import Mediator
from mediary.behaviors import LoggingBehavior

from ... import application

INTENTS = f"{application.__name__}.intents"
# The sends' log: quiet in the CLI unless -v, which then shows each failure's traceback.
LOGGER = logging.getLogger("i18n_ai.mediator")


def build_mediator() -> Mediator:
    """The mediator, with every intent's handler found by scanning the application's intents,
    and each send logged (with -v); an LLM run is slow by nature, so slowness is not a warning."""
    mediator = Mediator()
    mediator.scan(INTENTS)
    mediator.use(LoggingBehavior(LOGGER, slow_after=None), order=-100)
    return mediator
