"""The agents' one way to the model. The graph's nodes ask it to classify a file or translate a
batch of messages; it holds the run's limit on calls at once."""

import asyncio
import json
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any, Protocol, cast

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from ....domain.exports.locale import LocaleCode, LocaleSchema, SourceFile, SourceUnit
from . import prompts
from .schemas import FileClassification, TranslationBatch

# The leaves of a file shown to the model to classify it.
_SAMPLE_LEAVES = 40
_SAMPLE_LENGTH = 160


@dataclass(frozen=True)
class BatchRequest:
    """A batch of one schema's units, with what went wrong with each the last time, if anything."""

    schema: LocaleSchema
    units: Sequence[SourceUnit]
    file: str
    subject: str | None
    context: str | None
    previous: dict[str, str] = field(default_factory=dict)
    problems: dict[str, list[str]] = field(default_factory=dict)


class ILlmGateway(Protocol):
    async def classify(self, file: SourceFile, source: LocaleCode) -> FileClassification: ...

    async def translate(self, batch: BatchRequest) -> dict[str, str]:
        """The translations the model gave, by unit id; a missing id is left to the next attempt."""
        ...


class LangChainGateway:
    def __init__(self, model: BaseChatModel, concurrency: int) -> None:
        self._classifier = model.with_structured_output(FileClassification)
        self._translator = model.with_structured_output(TranslationBatch)
        self._calls = asyncio.Semaphore(max(1, concurrency))

    async def classify(self, file: SourceFile, source: LocaleCode) -> FileClassification:
        assert file.document is not None
        sample: dict[str, Any] = {}
        for path, value in file.document.leaves():
            if len(sample) >= _SAMPLE_LEAVES:
                break
            sample[str(path)] = value[:_SAMPLE_LENGTH] if isinstance(value, str) else value
        messages = [
            SystemMessage(prompts.classify_system(source)),
            HumanMessage(
                prompts.classify_human(
                    str(file.name), json.dumps(sample, ensure_ascii=False, indent=1)
                )
            ),
        ]
        async with self._calls:
            answer = await self._classifier.ainvoke(messages)
        return cast(FileClassification, answer)

    async def translate(self, batch: BatchRequest) -> dict[str, str]:
        messages = [
            SystemMessage(
                prompts.translate_system(batch.schema, batch.file, batch.subject, batch.context)
            ),
            HumanMessage(
                prompts.translate_human(
                    batch.units, batch.previous, batch.problems, batch.schema.target
                )
            ),
        ]
        async with self._calls:
            answer = cast(TranslationBatch, await self._translator.ainvoke(messages))
        wanted = {unit.id for unit in batch.units}
        return {item.id: item.text for item in answer.translations if item.id in wanted}
