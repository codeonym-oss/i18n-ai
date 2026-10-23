from pathlib import Path

import typer

from ...application.ports.locale import TreeRequest
from ...domain.exports.locale import InvalidLocaleCode, LocaleCode, LocaleFormat


class MissingParameter(typer.BadParameter):
    """A parameter a command needs, missing where nothing can ask for it; worded as Click words
    its own: `Missing option '--target'.`"""

    def __init__(self, kind: str, hint: str) -> None:
        super().__init__("", param_hint=hint)
        self.kind = kind

    def format_message(self) -> str:
        return f"Missing {self.kind} {self.param_hint}."


def locales(values: list[str] | None) -> tuple[LocaleCode, ...]:
    """The locales of a repeatable option, each value possibly comma-separated: `-t fr,de -t ar`."""
    codes: list[LocaleCode] = []
    for value in values or []:
        for part in value.split(","):
            if not part.strip():
                continue
            try:
                codes.append(LocaleCode(part))
            except InvalidLocaleCode as error:
                raise typer.BadParameter(error.message) from error
    return tuple(codes)


def tree_request(
    path: Path,
    source: str | None,
    output: Path | None,
    include: list[str] | None,
    exclude: list[str] | None,
    format: LocaleFormat | None = None,
) -> TreeRequest:
    source_code = locales([source])[0] if source else None
    return TreeRequest(
        path=path,
        source=source_code,
        output=output,
        include=tuple(include or ()),
        exclude=tuple(exclude or ()),
        format=format,
    )
