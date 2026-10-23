import dataclasses
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
from ...domain.exports.locale import LocaleFormat, SourceLocaleUnknown
from ...domain.exports.provider import ModelSpec
from ...runtime.answers import Answers, load_answers
from .. import interactive
from ..common import (
    MissingParameter,
    PresetOption,
    locales,
    project_tree,
    run,
    tree_request,
    with_preset,
)
from ..rendering import render_receipt, render_scan


def generate(
    path: Annotated[
        Path | None,
        typer.Argument(
            help=(
                "A locale directory (locales/en), file (en.json), bundle, or the directory "
                "holding the locales. Default: where the project's preset keeps them; asked for "
                "at a terminal."
            ),
            show_default=False,
        ),
    ] = None,
    targets: Annotated[
        list[str] | None,
        typer.Option(
            "--target",
            "-t",
            help="A locale to generate; repeat, or separate with commas: -t fr,de -t ar.",
            show_default=False,
        ),
    ] = None,
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
    format: Annotated[
        LocaleFormat | None,
        typer.Option(
            "--format",
            "-f",
            help="Read only the locale files in this format, when the tree mixes several.",
            case_sensitive=False,
        ),
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
    no_input: Annotated[
        bool,
        typer.Option(
            "--no-input", help="Ask nothing: fail on what is missing, as on CI or when piped."
        ),
    ] = False,
    preset: PresetOption = None,
) -> None:
    """Generate target locales from the source locale tree, with an agent per file and locale.
    At a terminal, what is missing is asked for."""
    asking = interactive.is_interactive(no_input)
    codes = locales(targets)
    if targets is not None and not codes:
        raise typer.BadParameter("name at least one target locale", param_hint="--target")

    async def flow(app: Bootstrap) -> int:
        console, mediator, defaults = app.console, app.mediator, app.settings.generation
        project = Path.cwd()
        wizard = (
            interactive.Wizard(
                interactive.prompter(), mediator, console, project, load_answers(project)
            )
            if asking
            else None
        )

        async def confirm(question: str) -> bool:
            if wizard is not None:
                return await wizard.confirm(question)
            return Confirm.ask(question, console=console, default=True)

        # 0. What the run was not told, found from the project's preset or asked: the tree, its
        #    source, the targets, the output
        tree = tree_request(path or Path(), source, output, include, exclude, format)
        if path is not None:
            tree, _ = await with_preset(mediator, console, tree, preset, given=True)
        elif wizard is not None:
            preset_tree, match = await with_preset(mediator, console, tree, preset, given=False)
            picked = await wizard.tree(match)
            # The preset's format is for its own locales
            tree = dataclasses.replace(
                preset_tree if picked.resolve() == preset_tree.path.resolve() else tree, path=picked
            )
        else:
            detected = await project_tree(mediator, console, tree, preset)
            if detected is None:
                raise MissingParameter("argument", "'PATH'")
            tree = detected
        if wizard is None and targets is None:
            raise MissingParameter("option", "'--target'")
        targets_ = codes
        if wizard is not None:
            try:
                found = await mediator.send(ScanLocaleTreeQuery(tree))
            except SourceLocaleUnknown as error:
                if tree.source is not None:
                    raise
                tree = dataclasses.replace(tree, source=await wizard.source(error.details["found"]))
                found = await mediator.send(ScanLocaleTreeQuery(tree))
            if not targets_:
                targets_ = await wizard.targets(found.source, found.existing)
            if output is None and (path is None or not codes):
                tree = dataclasses.replace(tree, output=await wizard.output(found.root))

        # 1. The precheck: the tree, its files, and the plan for each target
        report = await mediator.send(ScanLocaleTreeQuery(tree, targets_))
        render_scan(console, report, overwrite)
        if not report.qualified:
            console.print("[red]No source file qualifies: nothing to translate.[/]")
            return 1
        if dry_run:
            return 0

        # 2. The model, its key, and its provider's package, installed on demand
        spec = model or defaults.model
        if not spec and wizard is not None:
            spec = await wizard.model()
        if not spec:
            console.print(
                "[red]Name the model with --model provider:model, or set I18N_AI_MODEL.[/]"
            )
            return 2
        status = await mediator.send(GetProviderStatusQuery(ModelSpec(spec)))
        if wizard is not None and status.key and not status.key_set:
            await wizard.key(status.provider, status.key)
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
            if not yes and not await confirm(question):
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
        if not yes and not await confirm(question):
            return 1
        if wizard is not None:
            wizard.remember(
                Answers(
                    tree=wizard.shown(tree.path),
                    source=tree.source.value if tree.source else None,
                    targets=[target.value for target in targets_],
                    output=wizard.shown(tree.output) if tree.output else None,
                    model=spec,
                )
            )

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
            GenerateLocalesCommand(tree, targets_, ModelSpec(spec), options)
        )
        render_receipt(console, generation)

        # 5. What to type to run it again without the questions
        if wizard is not None and wizard.asked:
            line = interactive.command_line(
                wizard.shown(tree.path),
                targets_,
                spec,
                tree.source,
                wizard.shown(tree.output) if tree.output else None,
                _flags(context, include, exclude, format, preset, overwrite, strict, classify),
            )
            console.print(f"\nTo run it again: [bold]{line}[/]")
        return 0 if generation.ok else 1

    run(flow)


def _flags(
    context: str | None,
    include: list[str] | None,
    exclude: list[str] | None,
    format: LocaleFormat | None,
    preset: str | None,
    overwrite: bool,
    strict: bool,
    classify: bool,
) -> list[str]:
    """The options a run was given that the equivalent command repeats."""
    flags = ["-c", context] if context else []
    for pattern in include or []:
        flags += ["--include", pattern]
    for pattern in exclude or []:
        flags += ["--exclude", pattern]
    if format is not None:
        flags += ["--format", format.value]
    if preset is not None:
        flags += ["--preset", preset]
    flags += [flag for flag, on in (("--overwrite", overwrite), ("--strict", strict)) if on]
    return flags if classify else [*flags, "--no-classify"]
