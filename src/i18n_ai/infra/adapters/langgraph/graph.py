"""The run: every file is classified in parallel, then every qualifying file is translated into
every target in parallel, each as an atom (see `atom`).

    START ─▶ classify ×files ─▶ plan ─▶ translate_file ×(files × targets) ─▶ END

A file the model says is not a locale document is reported and left out. A translation that
fails outright, as when the model is unreachable, is reported for its file and target only."""

import logging
import operator
from typing import Annotated, Any, TypedDict

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Send

from ....application.ports.locale import (
    EngineRequest,
    FileClassified,
    FileFailed,
    FileTranslated,
    TranslationJob,
)
from ....domain.exports.locale import SourceFile, qualify
from .atom import build_atom_graph
from .gateway import ILlmGateway

logger = logging.getLogger(__name__)


class RunState(TypedDict):
    request: EngineRequest
    classified: Annotated[list[FileClassified], operator.add]
    outcomes: Annotated[list[FileTranslated | FileFailed], operator.add]


class ClassifyTask(TypedDict):
    request: EngineRequest
    file: SourceFile


class TranslateTask(TypedDict):
    request: EngineRequest
    job: TranslationJob
    subject: str | None


def build_run_graph(gateway: ILlmGateway) -> CompiledStateGraph[Any, Any, Any, Any]:
    atom = build_atom_graph(gateway)

    async def classify(task: ClassifyTask) -> dict[str, Any]:
        request, file = task["request"], task["file"]
        qualification = qualify(file.document, file.error)
        if not qualification.qualifies or not request.settings.classify:
            event = FileClassified(file, qualification.qualifies, qualification.reason)
        else:
            try:
                answer = await gateway.classify(file, request.source)
                event = FileClassified(file, answer.qualifies, answer.reason, answer.subject)
            except Exception as error:
                # The rules already qualified it; if the model is down, its translation says so
                logger.warning("Could not classify %s: %r", file.name, error)
                event = FileClassified(file, True, qualification.reason)
        return {"classified": [event]}

    def plan(state: RunState) -> dict[str, Any]:
        return {}

    async def translate_file(task: TranslateTask) -> dict[str, Any]:
        job, settings = task["job"], task["request"].settings
        try:
            state = await atom.ainvoke(
                {
                    "source": task["request"].source,
                    "job": job,
                    "settings": settings,
                    "subject": task["subject"],
                },
                {"recursion_limit": 10 + 3 * settings.max_attempts},
            )
            outcome: FileTranslated | FileFailed = state["outcome"]
        except Exception as error:
            logger.debug("%s → %s failed", job.file.name, job.target, exc_info=True)
            outcome = FileFailed(job, _describe(error))
        return {"outcomes": [outcome]}

    def dispatch_files(state: RunState) -> list[Send] | str:
        request = state["request"]
        sends = [
            Send("classify", ClassifyTask(request=request, file=file)) for file in request.files
        ]
        return sends or END

    def dispatch_jobs(state: RunState) -> list[Send] | str:
        request = state["request"]
        sends: list[Send] = []
        for event in state["classified"]:
            if not event.qualifies or event.file.document is None:
                continue
            for target in request.targets:
                existing = request.existing.get((event.file.name, target.key))
                job = TranslationJob(event.file, event.file.document, target, existing)
                sends.append(
                    Send(
                        "translate_file",
                        TranslateTask(request=request, job=job, subject=event.subject),
                    )
                )
        return sends or END

    builder = StateGraph(RunState)
    # `Send` gives the fanned-out nodes inputs of their own, which StateGraph's types don't know
    builder.add_node("classify", classify)  # type: ignore[arg-type]
    builder.add_node("plan", plan)
    builder.add_node("translate_file", translate_file)  # type: ignore[arg-type]
    builder.add_conditional_edges(START, dispatch_files, ["classify", END])
    builder.add_edge("classify", "plan")
    builder.add_conditional_edges("plan", dispatch_jobs, ["translate_file", END])
    builder.add_edge("translate_file", END)
    return builder.compile(name="i18n-ai")


def _describe(error: BaseException) -> str:
    text = str(error).strip().splitlines()
    return f"{type(error).__name__}: {text[0]}" if text else type(error).__name__
