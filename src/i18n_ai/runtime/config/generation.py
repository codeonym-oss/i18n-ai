from pydantic import BaseModel, ConfigDict, Field


class GenerationConfig(BaseModel):
    """The defaults of a generation, which the CLI's options override.

    - `model`: the model, as `provider:model`; required, here or with `--model`.
    - `batch_size`: the messages sent in one call to the model.
    - `concurrency`: the calls to the model at once.
    - `max_attempts`: how often a message is translated before it falls back to its source."""

    model_config = ConfigDict(frozen=True)

    model: str | None = None
    batch_size: int = Field(default=40, ge=1, le=500)
    concurrency: int = Field(default=8, ge=1, le=128)
    max_attempts: int = Field(default=3, ge=1, le=10)
