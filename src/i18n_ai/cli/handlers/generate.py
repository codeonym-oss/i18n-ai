from pathlib import Path
from typing import Annotated

import typer
from rich.prompt import Confirm

from ...application.exports.locale import (
    GenerateLocalesCommand,
    GenerationOptions,
    ScanLocaleTreeQuery,
)
from ...application.exports.provider import GetProviderStatusQuery, InstallProviderCommand
from ...di import Bootstrap
from ...domain.exports.provider import ModelSpec
from ..common import locales, run, tree_request
from ..rendering import render_receipt, render_scan


def generate(
    path: Annotated[
        Path,
        typer.Argument(
            help=(
                "A locale directory (locales/en), file (en.json), bundle, or the directory "
                "holding the locales."
            )
        ),
    ],
    targets: Annotated[
        list[str],
        typer.Option(
            "--target",
            "-t",
            help="A locale to generate; repeat, or separate with commas: -t fr,de -t ar.",
        ),
    ],
    model: Annotated[
        str | None,
        typer.Option(
            "--model",
            "-m",
            help=(
                "provider:model, e.g. openai:gpt-4.1-mini or ollama:qwen2.5:14b. "
                "Default: I18N_AI_MODEL."
            ),
        ),
    ] = None,
    source: Annotated[
        str | None,
        typer.Option("--source", "-s", help="The source locale, when the tree has several."),
    ] = None,
    output: Annotated[
        Path | None,
        typer.Option(
            "--output", "-o", help="Where the target locales go; beside the source by default."
        ),
    ] = None,
    context: Annotated[
        str | None,
        typer.Option(
            "--context", "-c", help="What the website is, to set the tone and vocabulary."
        ),
    ] = None,
    include: Annotated[
        list[str] | None,
        typer.Option("--include", help="Only the source files matching this glob."),
    ] = None,
    exclude: Annotated[
        list[str] | None,
        typer.Option("--exclude", help="Leave out the source files matching this glob."),
    ] = None,
    overwrite: Annotated[
        bool,
        typer.Option(
            "--overwrite",
            help=(
                "Translate every message again, instead of keeping the existing good translations."
            ),
        ),
    ] = False,
    strict: Annotated[
        bool,
        typer.Option("--strict", help="Write no file with a message that kept failing the rules."),
    ] = False,
    classify: Annotated[
        bool,
        typer.Option(
            "--classify/--no-classify", help="Let the model confirm each file is a locale document."
        ),
    ] = True,
    batch_size: Annotated[
        int | None, typer.Option("--batch-size", min=1, help="Messages per call to the model.")
    ] = None,
    concurrency: Annotated[
        int | None, typer.Option("--concurrency", min=1, help="Calls to the model at once.")
    ] = None,
    max_attempts: Annotated[
        int | None,
        typer.Option(
            "--max-attempts",
            min=1,
            max=10,
            help="Attempts per message before it falls back to its source.",
        ),
    ] = None,
    temperature: Annotated[
        float | None,
        typer.Option(
            "--temperature", help="The model's temperature; the provider's default if unset."
        ),
    ] = None,
    yes: Annotated[
        bool,
        typer.Option(
            "--yes", "-y", help="Skip the confirmations, installing the provider if needed."
        ),
    ] = False,
    dry_run: Annotated[
        bool, typer.Option("--dry-run", help="Scan and show the plan, then stop.")
    ] = False,
) -> None:
    """Generate target locales from the source locale tree, with an agent per file and locale."""
    tree = tree_request(path, source, output, include, exclude)
    codes = locales(targets)
    if not codes:
        raise typer.BadParameter("name at least one target locale", param_hint="--target")

    async def flow(app: Bootstrap) -> int:
        console, mediator, defaults = app.console, app.mediator, app.settings.generation

        # 1. The precheck: the tree, its files, and the plan for each target
        report = await mediator.send(ScanLocaleTreeQuery(tree, codes))
        render_scan(console, report, overwrite)
        if not report.qualified:
            console.print("[red]No source file qualifies: nothing to translate.[/]")
            return 1
        if dry_run:
            return 0

        # 2. The model, and its provider's package, installed on demand
        spec = model or defaults.model
        if not spec:
            console.print(
                "[red]Name the model with --model provider:model, or set I18N_AI_MODEL.[/]"
            )
            return 2
        status = await mediator.send(GetProviderStatusQuery(ModelSpec(spec)))
        if status.installed:
            console.print(
                f"Model [cyan]{status.provider}:{status.model}[/] [dim]({status.package}, "
                "installed)[/]"
            )
        else:
            question = (
                f"The {status.provider} provider needs [bold]{status.package}[/], not installed. "
                "Install it now?"
            )
            if not yes and not Confirm.ask(question, console=console, default=True):
                return 1
            with console.status(f"Installing {status.package}…"):
                receipt = await mediator.send(InstallProviderCommand(status.provider))
            console.print(f"[green]✓[/] {receipt.package} installed")

        # 3. The go-ahead
        files = len(report.qualified)
        jobs = files * len(report.targets)
        names = ", ".join(target.locale for target in report.targets)
        messages = report.to_translate if not overwrite else "all"
        question = (
            f"Translate {files} file(s) into {names} ({jobs} agent(s), {messages} message(s))?"
        )
        if not yes and not Confirm.ask(question, console=console, default=True):
            return 1

        # 4. The generation
        options = GenerationOptions(
            context=context,
            batch_size=batch_size or defaults.batch_size,
            concurrency=concurrency or defaults.concurrency,
            max_attempts=max_attempts or defaults.max_attempts,
            classify=classify,
            overwrite=overwrite,
            strict=strict,
            temperature=temperature,
        )
        generation = await mediator.send(
            GenerateLocalesCommand(tree, codes, ModelSpec(spec), options)
        )
        render_receipt(console, generation)
        return 0 if generation.ok else 1

    run(flow)
