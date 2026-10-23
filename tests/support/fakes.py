"""What stands in for the model: a gateway that 'translates' by tagging each message with the
target, keeping its placeholders, and can be told to break some messages first; a model list
that needs no network; and a dishka provider that puts them in the container, with every
provider installed and no progress bar. A keyring in memory. And a terminal: a prompter that
answers from a script."""

import re
from collections.abc import Collection, Sequence
from dataclasses import dataclass, field

from dishka import Provider, Scope, provide
from keyring.backend import KeyringBackend
from keyring.errors import PasswordDeleteError

from i18n_ai.application.ports.locale import ITranslationEngine
from i18n_ai.application.ports.progress import IGenerationProgress
from i18n_ai.application.ports.provider import (
    IModelLister,
    IProviderCatalog,
    ModelInfo,
    ModelListing,
)
from i18n_ai.cli.interactive import Choice, Prompter
from i18n_ai.domain.exports.locale import LocaleCode, SourceFile, SourceUnit, laravel_forms
from i18n_ai.infra.adapters.langchain import LangChainChatModels, LangChainProviderCatalog
from i18n_ai.infra.adapters.langgraph import (
    BatchRequest,
    FileClassification,
    LangGraphTranslationEngine,
)


class FakeGateway:
    def __init__(
        self, *, broken_first: set[str] | None = None, refuse: set[str] | None = None
    ) -> None:
        self.broken_first = (
            broken_first or set()
        )  # keys whose first translation loses its placeholders
        self.refuse = refuse or set()  # file names the classifier refuses
        self.batches: list[BatchRequest] = []
        self.classified: list[str] = []

    async def classify(self, file: SourceFile, source: LocaleCode) -> FileClassification:
        self.classified.append(str(file.name))
        refused = str(file.name) in self.refuse
        return FileClassification(qualifies=not refused, reason="fake", subject="tests")

    async def translate(self, batch: BatchRequest) -> dict[str, str]:
        self.batches.append(batch)
        out: dict[str, str] = {}
        for unit in batch.units:
            text = _tagged(unit, batch.schema.target)
            if str(unit.path) in self.broken_first and unit.id not in batch.problems:
                text = re.sub(r"\{\{[^}]*\}\}|(?<![A-Za-z0-9_]):[A-Za-z_][A-Za-z0-9_]*", "", text)
            out[unit.id] = text
        return out


def _tagged(unit: SourceUnit, target: LocaleCode) -> str:
    """The unit's source tagged with the target; a pipe plural in the target's shape, its
    ranges first in their forms."""
    pipes = unit.signature.pipes
    if pipes is None:
        return f"[{target}] {unit.source}"
    if any(pipes.ranges):
        forms = [
            f"{found or ''}[{target}]{form}"
            for found, form in zip(pipes.ranges, pipes.forms, strict=True)
        ]
    else:
        count = len(laravel_forms(target))
        forms = [f"[{target}] {pipes.forms[min(i, len(pipes.forms) - 1)]}" for i in range(count)]
    return "|".join(forms)


class InstalledCatalog(LangChainProviderCatalog):
    def is_installed(self, module: str) -> bool:
        return True


class FakeModelLister(IModelLister):
    """openai lists its models; any other provider's list cannot be read."""

    async def models(self, provider: str) -> ModelListing:
        if provider == "openai":
            models = (
                ModelInfo("fake-model", created=1_700_000_000),
                ModelInfo("old-model", created=1_600_000_000),
                ModelInfo("gpt-4.1-mini", created=1_650_000_000, rank=0),
            )
            return ModelListing(models, live=True)
        recommended = (ModelInfo(f"{provider}-pick", rank=0),)
        return ModelListing(recommended, live=False, problem="FAKE_API_KEY is not set")


class MemoryKeyring(KeyringBackend):
    """The system keyring, in memory: (service, user) -> password."""

    priority = 1  # type: ignore[assignment]

    def __init__(self) -> None:
        super().__init__()
        self.passwords: dict[tuple[str, str], str] = {}

    def get_password(self, service: str, username: str) -> str | None:
        return self.passwords.get((service, username))

    def set_password(self, service: str, username: str, password: str) -> None:
        self.passwords[(service, username)] = password

    def delete_password(self, service: str, username: str) -> None:
        if self.passwords.pop((service, username), None) is None:
            raise PasswordDeleteError(username)


class SilentProgress(IGenerationProgress):
    def start(self, jobs: int) -> None: ...
    def drop(self, jobs: int, reason: str) -> None: ...
    def advance(self, description: str) -> None: ...
    def finish(self) -> None: ...


class FakeModel(Provider):
    scope = Scope.APP

    def __init__(self, gateway: FakeGateway) -> None:
        super().__init__()
        self.gateway = gateway

    @provide
    def engine(self, models: LangChainChatModels) -> ITranslationEngine:
        return LangGraphTranslationEngine(models, gateways=lambda settings: self.gateway)

    catalog = provide(InstalledCatalog, provides=IProviderCatalog)
    models = provide(FakeModelLister, provides=IModelLister)
    progress = provide(SilentProgress, provides=IGenerationProgress)


@dataclass
class Asked:
    kind: str
    message: str
    choices: list[str] = field(default_factory=list)
    default: object = None


class ScriptedPrompter(Prompter):
    """Answers each question with the next answer of the script, and records what was asked. A
    choice can be answered with its value or its title."""

    def __init__(self, *answers: object) -> None:
        self.answers = list(answers)
        self.asked: list[Asked] = []

    def _next(self, asked: Asked) -> object:
        self.asked.append(asked)
        assert self.answers, f"nothing scripted to answer {asked}"
        return self.answers.pop(0)

    @staticmethod
    def _pick(answer: object, choices: Sequence[Choice]) -> str:
        for choice in choices:
            if answer in (choice.value, choice.title):
                return choice.value
        raise AssertionError(f"{answer!r} is not among {[c.value for c in choices]}")

    async def select(
        self, message: str, choices: Sequence[Choice], default: str | None = None
    ) -> str:
        answer = self._next(Asked("select", message, [c.value for c in choices], default))
        return self._pick(answer, choices)

    async def checkbox(
        self, message: str, choices: Sequence[Choice], checked: Collection[str] = ()
    ) -> list[str]:
        answer = self._next(Asked("checkbox", message, [c.value for c in choices], set(checked)))
        assert isinstance(answer, list)
        return [self._pick(item, choices) for item in answer]

    async def text(self, message: str, default: str = "") -> str:
        return str(self._next(Asked("text", message, default=default)))

    async def secret(self, message: str) -> str:
        return str(self._next(Asked("secret", message)))

    async def confirm(self, message: str, default: bool = True) -> bool:
        return bool(self._next(Asked("confirm", message, default=default)))
