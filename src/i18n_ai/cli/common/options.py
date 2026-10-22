from pathlib import Path

import typer

from ...application.ports.locale import TreeRequest
from ...domain.exports.locale import InvalidLocaleCode, LocaleCode


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
) -> TreeRequest:
    source_code = locales([source])[0] if source else None
    return TreeRequest(
        path=path,
        source=source_code,
        output=output,
        include=tuple(include or ()),
        exclude=tuple(exclude or ()),
    )
