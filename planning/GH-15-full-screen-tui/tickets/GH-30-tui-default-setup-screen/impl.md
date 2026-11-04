# Implementation: open a full-screen TUI by default, starting with its setup screen

Planned 2026-10-26 against `main` at `8287930`. Baseline: 338 tests pass, coverage 94.27%.

Rests on story decisions 003 (no strict), 006 (the TUI is the default, Textual a dependency), 007 (`cli/tui/`, a
contract keeps `textual` in it), and this ticket's 001 (`cli/common/setup.py`), 002 (`Bootstrap` takes a progress),
003 (one form), 004 (Run is the go-ahead; the receipt says how to run it again).

## Read first

- `src/i18n_ai/cli/app.py`: `root`, whose bare call at a terminal runs `generate()` today.
- `src/i18n_ai/cli/handlers/generate.py`: `flow`, the steps the form replaces (preset and tree, source when unknown,
  targets, output, precheck, model, key, install, answers, options, receipt, `command_line`).
- `src/i18n_ai/cli/interactive/wizard.py`: the choice builders inside `tree`, `targets`, `output`, `model`; `key`;
  `shown`; `command_line`.
- `src/i18n_ai/cli/common/presets.py` (`with_preset`, `project_tree`), `runner.py` (`run`, the consoles).
- `src/i18n_ai/di/bootstrap.py`, `di/container.py`, `di/platform/console.py`: where the progress is provided.
- `src/i18n_ai/cli/rendering/receipt.py`: `render_receipt(console, receipt)` prints; the TUI renders it into a
  recording console.
- `src/i18n_ai/runtime/answers.py`, `runtime/settings.py`: `Answers`, the generation defaults.
- `tests/cli/test_interactive.py`, `tests/cli/test_cli.py`: the fake model through `bootstrap.build_container`, the
  scripted prompter; they guard the refactor.
- acli-py's `src/acli_py/presentation/tui/` for Textual idioms used in the org (screens, bindings, CSS, Pilot tests).

## Steps

1. **`cli/common/setup.py`, by moving code (decision 001).** Out of `Wizard` and `generate.flow`, with no change in
   behaviour:
   - `tree_choices(candidates, preset, last, shown) -> (choices, default)`, `locale_choices(known, existing,
     source, last) -> (choices, checked)`, `output_choices(beside, last, shown)`, `provider_choices(providers,
     last)`, `model_choices(listing, provider, last)`; the titles (`_title`, `_some`, `_provider_title`) move with
     them.
   - `generation_options(defaults, **given) -> GenerationOptions` and `answers_of(tree, targets, spec, shown)`.
   The `Wizard` asks with these; `generate.flow` calls them.
   → check: `tests/cli/test_interactive.py` and `tests/cli/test_cli.py` pass unchanged; a short unit test per
   builder in `tests/cli/test_setup.py` (the preset's tree first, "in the tree" locales checked, providers with a key
   or installed first).
2. **`Bootstrap(settings, console, progress=None)` (decision 002).** Given one, `build_container` gets a provider
   in `di` giving it as `IGenerationProgress`, after `ConsoleProvider`, so it wins.
   → check: a test in `tests/test_bootstrap.py` (new) or `tests/cli`: a run through `Bootstrap` with a recording
   progress sees `start` and `finish`; without one, today's CLI tests pass.
3. **Textual, and the contract.** `uv add textual` (latest; `--safe-chain-skip-minimum-package-age` if the proxy
   blocks it). In `pyproject.toml`, a forbidden contract: `textual` only from `i18n_ai.cli.tui`; `textual` added to
   the pure-core contract's forbidden list. Ruff's `RUF012` ignored for `src/i18n_ai/cli/tui/**` (Textual's
   `BINDINGS` and `CSS`), as acli-py does.
   → check: `uv run lint-imports` passes; importing `textual` from `i18n_ai.cli.handlers` makes it fail (tried, then
   reverted).
4. **The app and the default mode.** `cli/tui/app.py`: `I18nAiApp(App)`, entering `Bootstrap(settings,
   Console(quiet=True), progress=TuiProgress(...))` in `on_mount` (Textual's loop), closing it on exit; the
   project's preset detected and shown in the header. `cli/app.py`: `i18n-ai tui` runs it; bare `i18n-ai` at a
   terminal runs it instead of `generate()`; off a terminal, the help, as today. The refusals (`DomainException`,
   `ApplicationException`, `InfraException`) show in a notification rather than ending the app.
   → check: a CLI test: bare `i18n-ai` with `is_interactive` false prints the help; with it true, the app's `run` is
   called (patched). `i18n-ai generate` with every argument unchanged (existing tests).
5. **The setup screen (decision 003).** `cli/tui/setup.py`: the form in two groups, its fields filled from step 1's
   builders through the mediator's queries, defaults from the last answers. A field is disabled until its inputs
   are set; the source field shows only when the scan raises `SourceLocaleUnknown`. Targets: a searchable
   selection list. Key: shown as set, or a password input with "save in the keyring" (`SetProviderKeyCommand`), as
   the wizard does. The files · locales line from a `ScanLocaleTreeQuery` when tree and targets change.
   → check: Pilot tests: on `examples/i18next` the tree is preselected, `fr` is checked "in the tree", the model
   field is disabled until a provider is picked; a missing key shows the password input.
6. **Run (decision 004).** `Ctrl+R` / the button: no confirmation; a missing provider package asks "Install
   `<package>`?" in a modal (`InstallProviderCommand`; no returns to the form); the answers are remembered;
   `GenerateLocalesCommand` sent with `generation_options(...)` (no strict).
   → check: a Pilot test with the fake model on `examples/i18next` fills the form, runs, and finds the targets
   written.
7. **The run and the receipt.** `cli/tui/progress.py`: `TuiProgress(IGenerationProgress)` posting to a run screen,
   a progress bar and a line per file × locale done. Then the receipt: `render_receipt` into a recording `Console`,
   shown in the screen, and "To run it again: …" from `command_line`; `b` back to the setup, `q` quit.
   → check: the Pilot test of step 6 reads the receipt's table and the command line.
8. **Palette and bindings.** The palette's commands: Run, Back to setup, Quit (Textual's `CommandPalette` with a
   `Provider`); every action has a binding shown in the footer; the layout reflows at 80 columns.
   → check: a Pilot test opens the palette with `Ctrl+P` and runs "Quit"; a Pilot test at 80×24 sees every field.
9. **Docs.** `docs/guide/getting-started.md`: `i18n-ai` opens the TUI (a screenshot from Textual's
   `save_screenshot` as SVG, like acli-py's); the prompts stay for `i18n-ai generate` at a terminal. README's
   quick start likewise.
   → check: the docs build with `-W`.

## Tests

- Unit: the choice builders (`tests/cli/test_setup.py`).
- `Bootstrap` with a given progress.
- CLI: the default mode chooses the TUI at a terminal and the help elsewhere.
- Pilot (`tests/tui/test_setup.py`, new): the form's defaults and dependencies, the key input, a full run with the
  fake model to the receipt, the palette, 80×24.
- The existing CLI and interactive tests guard the refactor of step 1.

## Risks

- **The refactor of step 1** touches the wizard every prompt goes through: done first, as pure moves, with the
  existing interactive tests green before anything new.
- **Printing inside Textual:** anything still writing to stdout (a `print`, a logger's `RichHandler` on stderr from
  `root`) garbles the screen. The app's logging goes to Textual's log while it runs; checked by running
  `i18n-ai` by hand on `examples/laravel`.
- **Pilot timing:** the run is async in Textual's loop; tests wait on the receipt screen (`pilot.wait_for_scheduled_animations`,
  or polling the screen stack) rather than sleeping.
- **Windows:** Textual supports it; the matrix's Windows job runs the Pilot tests.

## As built (2026-10-26)

Changed from the plan, none of them a change of design:

- `Choice` moved to `cli/common/setup.py` (the prompter imports it from there), so `common` does
  not import `interactive`. `setup.py` also holds `source_choices`, `within` (paths shown
  relative to the project) and `command_line`.
- The bare-`i18n-ai` interactive test now runs `i18n-ai generate`, since bare `i18n-ai` opens the
  TUI; a new test checks that. The other interactive and CLI tests are unchanged.
- The Textual contract covers all of `i18n_ai`, with `cli.tui` ignored, so a future `cli/shell/`
  is checked too. `runner.valid_settings` is shared by `run` and `i18n-ai tui`.
- The TUI's default model is `I18N_AI_MODEL`, else the last answer, as `generate` takes it.
- When no tree is found, the tree field is a path typed in (the prompts' "Another path…"); there
  is no "another path / directory / model" otherwise.
- The Pilot tests are `tests/tui/test_tui.py` (`tests/cli/test_setup.py` holds the builders').
- The palette's commands come through `App.get_system_commands`, Textual's system provider.
- Checked by hand: `i18n-ai -vv` in `examples/laravel` draws the form, no log line leaks, `q`
  quits.
