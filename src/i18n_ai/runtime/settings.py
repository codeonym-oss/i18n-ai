"""i18n-ai's settings, read from the environment once, at start. A `.env` in the working
directory is read first, without overriding what the environment already sets; it is also
where the providers' keys (OPENAI_API_KEY, ANTHROPIC_API_KEY, ...) can go."""

import logging
import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel, ConfigDict

from .config import GenerationConfig

logger = logging.getLogger(__name__)

# Each from I18N_AI_<NAME>, keeping GenerationConfig's default when unset.
GENERATION = ("model", "batch_size", "concurrency", "max_attempts")


class Settings(BaseModel):
    model_config = ConfigDict(frozen=True)

    generation: GenerationConfig


def build_settings() -> Settings:
    env = Path.cwd() / ".env"
    if env.is_file():
        load_dotenv(env, override=False)
        logger.debug("Read %s", env)

    values: dict[str, str] = {}
    for name in GENERATION:
        value = os.getenv(f"I18N_AI_{name.upper()}")
        if value:
            values[name] = value
    return Settings(generation=GenerationConfig.model_validate(values))
