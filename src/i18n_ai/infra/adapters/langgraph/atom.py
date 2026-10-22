"""The atom: one source file into one target locale, as a graph of its own.

    extract_schema ─▶ translate ─▶ validate ─▶ assemble
                         ▲            │
                         └── retry ◀──┘  (the rejected messages, with their problems)

`extract_schema` takes the target's shape from the source (its plural categories included),
and keeps the existing target's good translations. `translate` sends the rest to the model in
batches; `validate` checks each answer against the rules, and sends the rejected ones back
with what is wrong, until they pass or the attempts run out. `assemble` builds the document; a
message that never passed keeps its source text, and is reported."""

import asyncio
import logging
from typing import Any, Literal, TypedDict

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from ....application.ports.locale import EngineSettings, FileTranslated, TranslationJob
from ....domain.exports.locale import (
    LocaleCode,
    LocaleSchema,
    Severity,
    Violation,
    check,
    extract_schema,
    fallback,
    normalize,
    reusable_translations,
)
from .gateway import BatchRequest, ILlmGateway

logger = logging.getLogger(__name__)


class AtomState(TypedDict, total=False):
    # In
    source: LocaleCode
    job: TranslationJob
    settings: EngineSettings
    subject: str | None
    # Worked out
    schema: LocaleSchema
    done: dict[str, str]
    reused: int
    pending: list[str]
    drafts: dict[str, str]
    previous: dict[str, str]
    problems: dict[str, list[str]]
    failures: dict[str, list[Violation]]
    warnings: list[Violation]
    attempt: int
    # Out
    outcome: FileTranslated


def build_atom_graph(gateway: ILlmGateway) -> CompiledStateGraph[Any, Any, Any, Any]:
    def extract(state: AtomState) -> AtomState:
        job = state["job"]
        schema = extract_schema(job.document, state["source"], job.target)
        reused = reusable_translations(schema, job.existing)
        pending = [unit.id for unit in schema.units if unit.id not in reused]
        return {
            "schema": schema,
            "done": dict(reused),
            "reused": len(reused),
            "pending": pending,
            "previous": {},
            "problems": {},
            "failures": {},
            "warnings": [],
            "attempt": 0,
        }

    async def translate(state: AtomState) -> AtomState:
        schema, settings, job = state["schema"], state["settings"], state["job"]
        units = [schema.unit(unit_id) for unit_id in state["pending"]]
        size = max(1, settings.batch_size)
        batches = [
            BatchRequest(
                schema=schema,
                units=units[start : start + size],
                file=str(job.file.name),
                subject=state.get("subject"),
                context=settings.context,
                previous={
                    unit.id: state["previous"][unit.id]
                    for unit in units[start : start + size]
                    if unit.id in state["previous"]
                },
                problems={
                    unit.id: state["problems"][unit.id]
                    for unit in units[start : start + size]
                    if unit.id in state["problems"]
                },
            )
            for start in range(0, len(units), size)
        ]
        answers = await asyncio.gather(
            *(gateway.translate(batch) for batch in batches), return_exceptions=True
        )

        drafts: dict[str, str] = {}
        errors = [answer for answer in answers if isinstance(answer, BaseException)]
        for answer in answers:
            if isinstance(answer, dict):
                drafts.update(answer)
        if errors and len(errors) == len(answers):
            # Not one batch came back: the model is unreachable, or refuses; nothing to retry
            raise errors[0]
        for error in errors:
            logger.warning(
                "A batch of %s → %s failed, and is retried: %r", job.file.name, job.target, error
            )
        return {"drafts": drafts, "attempt": state["attempt"] + 1}

    def validate(state: AtomState) -> AtomState:
        schema = state["schema"]
        done = dict(state["done"])
        warnings = list(state["warnings"])
        pending: list[str] = []
        previous: dict[str, str] = {}
        problems: dict[str, list[str]] = {}
        failures: dict[str, list[Violation]] = {}
        for unit_id in state["pending"]:
            unit = schema.unit(unit_id)
            draft = state["drafts"].get(unit_id)
            text = normalize(unit, draft) if draft is not None else None
            violations = check(schema, unit, text)
            rejected = [
                violation for violation in violations if violation.severity == Severity.ERROR
            ]
            if not rejected and text is not None:
                done[unit_id] = text
                warnings.extend(violations)
                continue
            pending.append(unit_id)
            failures[unit_id] = rejected
            problems[unit_id] = [violation.message for violation in rejected]
            if text is not None:
                previous[unit_id] = text
        return {
            "done": done,
            "warnings": warnings,
            "pending": pending,
            "previous": previous,
            "problems": problems,
            "failures": failures,
        }

    def assemble(state: AtomState) -> AtomState:
        schema = state["schema"]
        failed = {unit_id: state["failures"].get(unit_id, []) for unit_id in state["pending"]}
        content = schema.render({**state["done"], **fallback(schema, failed)})
        reused = state["reused"]
        return {
            "outcome": FileTranslated(
                job=state["job"],
                content=content,
                translated=len(state["done"]) - reused,
                reused=reused,
                failures=tuple(
                    violation for violations in failed.values() for violation in violations
                ),
                warnings=tuple(state["warnings"]),
            )
        }

    def after_extract(state: AtomState) -> Literal["translate", "assemble"]:
        return "translate" if state["pending"] else "assemble"

    def after_validate(state: AtomState) -> Literal["translate", "assemble"]:
        if state["pending"] and state["attempt"] < state["settings"].max_attempts:
            return "translate"
        return "assemble"

    builder = StateGraph(AtomState)
    builder.add_node("extract_schema", extract)
    builder.add_node("translate", translate)
    builder.add_node("validate", validate)
    builder.add_node("assemble", assemble)
    builder.add_edge(START, "extract_schema")
    builder.add_conditional_edges("extract_schema", after_extract, ["translate", "assemble"])
    builder.add_edge("translate", "validate")
    builder.add_conditional_edges("validate", after_validate, ["translate", "assemble"])
    builder.add_edge("assemble", END)
    return builder.compile(name="atom")
