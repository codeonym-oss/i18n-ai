# Implementation: the plan screen, and single cells turned off

Written 2026-10-29 against `main` at 3d271ba. Rests on story decisions 003 and 005, GH-30's decisions 002–004,
and this ticket's 001–005.

**Before starting:** `main` fails 7 tests (4 in `tests/tui/test_tui.py`, 3 in `tests/integration/test_generate.py`)
because of untracked run output in `examples/i18next/locales/` (`de/`, `es/`, `fr/auth/`), which the `examples`
fixture copies. They go first (the person's call), so the build starts green.

## Read first

- `src/i18n_ai/application/intents/locale/commands/generate_locales/cmd.py`: `GenerateLocalesCommand`.
- `src/i18n_ai/application/intents/locale/commands/generate_locales/handler.py`: steps 2–4 (qualified files,
  existing targets with the record, `EngineRequest`, `progress.start`, `FileClassified` → `progress.drop`).
- `src/i18n_ai/application/ports/locale/engine.py`: `EngineRequest`.
- `src/i18n_ai/infra/adapters/langgraph/graph.py`: `dispatch_files`, `dispatch_jobs`.
- `src/i18n_ai/application/intents/locale/queries/scan_locale_tree/handler.py`: the precheck's counts.
- `src/i18n_ai/domain/sub_domains/locale/vo/locale_code.py`: `LocaleCode.key`.
- `src/i18n_ai/cli/tui/setup.py`: `_run`, `action_run`, the `#run` button and `#plan` line.
- `src/i18n_ai/cli/tui/run.py`, `confirm.py`, `app.py` (`get_system_commands`).
- `src/i18n_ai/cli/common/setup.py`: `command_line`.
- `tests/integration/test_generate.py` (`generate`, `Stubborn`, the record tests), `tests/tui/test_tui.py`,
  `tests/support/fakes.py` (`FakeGateway.batches`, `.classified`).
- Docs: `docs/guide/getting-started.md` ("Just run it"), `docs/reference/commands.md` (`i18n-ai tui`),
  `docs/guide/tui.svg`, `README.md` line 65.

## Steps

1. **The skip set on the command and the engine request** (decision 002). `GenerateLocalesCommand.skip:
   frozenset[tuple[PurePosixPath, LocaleCode]] = frozenset()`, documented as the (file name, target) pairs left out.
   `EngineRequest.skip: frozenset[tuple[PurePosixPath, str]] = frozenset()`, keyed by the target's `key` as
   `existing` is. `dispatch_jobs` sends no job for a pair in it.
   → check: a new integration test, *a skipped pair is never translated*: i18next tree, targets `fr`, `de`, skip
   (`common.json`, `de`); no batch for `common.json` → `de` (`gateway.batches`' schema target), the other three
   jobs written, the receipt has no `common.json` → `de` row, `de/common.json` not written.

2. **The handler leaves skipped work out** (decision 002). It turns `command.skip` into keys once; a qualified file
   whose every target is skipped is not sent to the engine (not classified, no receipt row); no existing target is
   read for a skipped pair; `progress.start` gets the jobs that remain; a `FileClassified` that does not qualify
   drops that file's unskipped targets only.
   → check: integration tests *a file with every target skipped is not classified* (`gateway.classified`) and, in
   `tests/test_bootstrap.py`, *the progress counts the jobs left* (`RecordingProgress` sees `start 3` for 2 files ×
   2 targets, one skipped).

3. **The precheck counts recorded fallbacks** (decision 003). `ScanLocaleTreeQueryHandler` takes `IFallbackRecord`,
   reads it for `tree.target_directory`, and counts reusable messages on `existing.without(paths)` with the paths
   recorded for that target (the generate handler's `_record_target` match; move it to `application/common/` if
   both need it, rather than copying it).
   → check: integration test *a recorded fallback counts as to translate*: after a `Stubborn` run into `it`, the
   scan's `it` / `common.json` has `to_translate == 1`. The existing scan and `i18n-ai check` tests still pass.

4. **The plan's arguments from the cells off** (decisions 004, 005). A pure function in `cli/common/setup.py`,
   `planned(files, targets, off) -> Planned(targets, exclude, skip)`: a locale whose every cell is off leaves
   `targets`; a file whose every cell is off becomes an `exclude` pattern (its name with glob characters escaped);
   the cells left go to `skip`. The `exclude` patterns reach `command_line` as `--exclude` words in its
   existing `flags` (corrected while building: its signature needs no change).
   → check: unit tests in `tests/cli/test_setup.py`: a full column, a full row, a single cell, and a name with
   `[` in it that the scanner's `fnmatch` still matches only itself.

5. **The plan screen** (decision 005). `cli/tui/plan.py`, `PlanScreen(Screen[Planned | None])`, given the
   `ScanReport`: a `DataTable` with a cell cursor, a row per qualified file, a column per target; cells **new N**,
   **fill N**, **up to date**, **off**; the files that do not qualify listed under it with their reason; a total
   line "N jobs · M messages" that follows the cells. Bindings: **space** cell, **r** row, **c** column (all off,
   or all on when all are off), **ctrl+r** Run (refused with a notice when every cell is off), **b**/escape back
   (dismiss `None`). The palette gets "Run" on the plan screen (`app.py`).
   → check: Pilot tests: the cells of the i18next example read as expected; space, r and c toggle and the total
   follows; Run with every cell off is refused.

6. **Setup leads to the plan** (decision 001). The `#run` button becomes `#next`, labelled **Plan**; `ctrl+r` is
   "Plan", and so is the palette's command on the setup screen. `_run` keeps its checks, key, install
   and remembered answers, then runs the scan, pushes `PlanScreen` with `push_screen_wait`; `None` returns to the
   form; a `Planned` builds the command with its `targets`, `TreeRequest(exclude=…)` added to the setup's own, and
   `skip`, pushes `RunScreen` and runs as today. "To run it again" is `command_line` with the `--exclude` flags,
   and when `skip` is not empty a line under it: "N single cells were off; this command runs them too."
   (`RunScreen.show_receipt` takes that note). Back from the receipt goes to the setup form.
   → check: the existing run and install tests go through the plan (`ctrl+r` twice); a new Pilot test, *a cell
   turned off is not written*: i18next example, targets `fr`, `de`, turn off `common.json` × `de`, run; `de/`
   has `auth/login.json` but not `common.json`, and the receipt shows the note.

7. **Docs.** Getting started: setup → plan → run, the cell states and keys; `commands.md`'s `i18n-ai tui`; the
   README line ("a form, a plan, a run, and the receipt"); a new `docs/guide/tui-plan.svg` screenshot from the
   fakes, as `tui.svg` was made.
   → check: `uv run --frozen sphinx-build -W --keep-going -b dirhtml docs docs/_build/html`.

8. **Everything.** `uv run --frozen ruff check . && uv run --frozen ruff format --check .`,
   `uv run --frozen mypy`, `uv run --frozen lint-imports`, `uv run --frozen pytest` (coverage ≥ 85 %), and by hand:
   `i18n-ai` in `examples/i18next` (on a copy), Plan, turn a cell off, Run.

## Tests

- **Application, through the mediator with the fake model** (`tests/integration/test_generate.py`): the skipped
  pair (step 1), the fully skipped file (2), the precheck with a record (3).
- **Bootstrap** (`tests/test_bootstrap.py`): the progress count (2).
- **Pure** (`tests/cli/test_setup.py`): `planned` and `command_line`'s `--exclude` (4).
- **Pilot** (`tests/tui/test_tui.py`): the grid and its keys (5), the flow and a cell off on disk (6), and the
  80×24 test extended to the plan screen.

## Risks

- **The engine port changes:** `EngineRequest` gains a field with a default, so other builders of it (tests, the
  fake) are untouched; `dispatch_jobs` is the only reader. Checked by the full integration suite.
- **The precheck's counts change** for trees with a record, in the CLI's `check`/prompts too: intended (decision
  003), and only there; the other scan tests prove nothing else moves.
- **`exclude` by file name:** a name with glob characters must match only itself; step 4's test covers it.
- **The flow change** touches every Pilot test that presses `ctrl+r`; they are updated in step 6, not loosened.
- **Narrow terminals:** many locales make the table wide; `DataTable` scrolls sideways; the 80×24 test checks the
  footer and the total line stay visible.

## Follow-ups noted, not done here

- A CLI `--skip file:locale` (story decision 005).
- "Another path…" / "Another model…" in the setup form (from GH-30's as-built notes), if the person wants it saved.
