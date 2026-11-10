# Implementation: open the TUI on the Aurora shell and its Home

Planned 2026-11-10 against `main` at 004f8e1. Story decisions 001–007, ticket decisions 001–006.

## Read first

- `src/i18n_ai/cli/tui/app.py`: `I18nAiApp`. Today it pushes `SetupScreen` on one stack in `on_mount`, and
  `get_system_commands` adds the palette's commands for each screen.
- `src/i18n_ai/cli/tui/setup.py`:
  - `SetupScreen.on_mount` (lines 157–185) picks the tree with `with_preset`, `DetectLocaleTreesQuery` and
    `tree_choices`;
  - `_run` (lines 417–489) is a worker that pushes `PlanScreen` with `push_screen_wait`, then `RunScreen`;
  - `action_review` and `_review_screen` (lines 281–287).
- `src/i18n_ai/cli/tui/run.py`: `RunScreen`, its `_review` callback and `action_review` (lines 113–147).
- `src/i18n_ai/cli/tui/review.py`: `ReviewScreen(mediator, tree, model, options)`. It already handles
  `model=None`, which turns retry off and shows a hint.
- `src/i18n_ai/cli/tui/plan.py`, `confirm.py`: `PlanScreen`, and `ConfirmScreen`, which stays a modal.
- `src/i18n_ai/cli/common/setup.py`: `tree_choices`, which gives the default tree.
- `src/i18n_ai/application/intents/locale/queries/scan_locale_tree/view.py`:
  - `ScanReport` with its `existing`, `output` and `targets`;
  - `TargetFileView` with its `path`, `bundle_key`, `reusable` and `to_translate`.
  - The query takes its targets explicitly.
- `src/i18n_ai/application/intents/locale/queries/list_fallbacks/view.py` and
  `application/ports/locale/fallbacks.py`:
  - `RecordedFallback.file` is relative to the record's directory, which is the scan's `output`;
  - `key` is the bundle key.
- `src/i18n_ai/runtime/answers.py`: `Answers.model`.
- `tests/tui/test_tui.py`: has the helpers `isolated`, `tui`, `settle`, `pick` and `ready`. It has 30 tests,
  all passing on 2026-11-10.
- `tests/conftest.py`: the `examples`, `state` and `vault` fixtures.
- `tests/support/fakes.py`: `FakeGateway`, which has no way to hold a run open.
- `docs/guide/getting-started.md`, "Just run it", and `docs/guide/tui.svg`.
- `pyproject.toml`: the `test` dependency group and the import-linter contract that keeps `textual` in `cli.tui`.

## Steps

1. **The snapshot fixture** (ticket decision 001).
   - Add `syrupy>=6.1.1` to the `test` group with `uv add --group test`. Use
     `--safe-chain-skip-minimum-package-age` if the age check refuses it. Never pin an older version.
   - Move `gateway`, `isolated` and the helpers `tui`, `settle`, `pick` and `ready` from `test_tui.py` into
     `tests/tui/conftest.py` (fixtures) and `tests/support/tui.py` (helpers). This lets the new test files share
     them.
   - Add a `snap` fixture in `tests/tui/conftest.py`. Given an app, a size and an optional async `setup(pilot)`,
     it runs `run_test(size=…)`, settles, and asserts that `app.export_screenshot()` matches syrupy's
     `SingleFileSnapshotExtension`, with the `.svg` extension, under `tests/tui/__snapshots__/`.
   - → check: the 30 TUI tests still pass after the move. A throwaway snapshot of today's setup screen at 100×40
     is written by `--snapshot-update`, then passes twice in a row without it, which proves the SVG is
     deterministic. Then delete it.

2. **The `aurora` theme** (story decision 003).
   - Write `cli/tui/aurora.py` with `AURORA = Theme(name="aurora", dark=True, …)`:
     - background #08070D;
     - surface #100F18 and panel #0C0B13;
     - primary violet #A99BFF;
     - accent and success mint #54E1B8;
     - warning amber #FFC46B;
     - error coral #FF7E93;
     - secondary sky #71B7FF.
   - Extra tokens go in `variables`: the five heat steps, and the border colours #1D1A2A, #26233A and #34304A.
   - `I18nAiApp` registers it and sets `theme = "aurora"`.
   - `get_system_commands` leaves out Textual's theme command.
   - → check: a Pilot test checks that `app.theme == "aurora"`, and that typing "theme" in the palette finds
     nothing.

3. **The kit** (story decision 003). In `cli/tui/kit/` add:
   - `Card`: a titled, rounded panel;
   - `KpiTile`: a label, a big value and a note;
   - `Chip`: a glyph and a word, in one of the tones;
   - `heat.py`: `shade(percent)`, which maps a percentage to one of the five steps (0, 1–39, 40–74, 75–99, 100),
     and `HeatCell`;
   - `KeyHints`.
   
   Shared rules go in `cli/tui/aurora.tcss`, which is the app's `CSS_PATH`. Only what Home and the shell use goes
   in now. Later tickets add what their screens need.
   - → check: a unit test for `shade` at 0, 1, 39, 40, 74, 75, 99 and 100, with the expected steps written as
     literals.

4. **`ShellScreen`** in `kit/shell.py` (ticket decision 002, story decisions 002 and 004).
   - `compose` yields these, and subclasses implement `body()`:
     - the sidebar, with Home, Run and Review, and Review's fallback-count badge;
     - the command bar, with the `ctrl+p` hint and the tree switcher (step 8);
     - `#body`;
     - the status line: a chip for the mode in the mode's colour, the screen's tree (a run's own tree,
       decision 004), and Textual's `Footer` in compact form for the bindings.
   - `on_resize` sets `-narrow` below 120 columns, which turns the sidebar into an icon rail and stacks the
     panels.
   - It shows a centred notice in place of `#body` below 80×24: "i18n-ai needs 80×24; this terminal is W×H".
   - → check: Pilot tests at 160×45 (the sidebar shows its labels), 100×30 (`-narrow`, the rail only) and
     70×20 (the notice shows and `#body` is hidden).

5. **The screens inside the shell.** `SetupScreen`, `PlanScreen`, `RunScreen` and `ReviewScreen` subclass
   `ShellScreen`.
   - Their `compose` becomes `body()`, without `Header`/`Footer`, and their contents don't change.
   - The `#form`-style ids stay, so the existing selectors still match.
   - → check: the 30 existing TUI tests pass. The two "fits 80 columns" tests still prove every field is on
     screen at 80×24.

6. **The modes and the section keys** (story decision 004, ticket decisions 003 and 006).
   - **The modes.** `I18nAiApp.MODES` has `home` (`HomeScreen`, step 7), `run` (`SetupScreen`, the arguments
     it takes today) and `review`. `on_mount` switches to `home`.
   - **The default tree.** The default-tree logic moves out of `SetupScreen.on_mount` into
     `cli/tui/trees.py`: `find_trees(mediator, quiet, project, last)`. It returns the choices, the default and
     the preset's request. `I18nAiApp` keeps the result and the current tree (`app.tree`), and setup starts
     from it.
   - **The section keys.** The app binds `ctrl+o` (Home), `ctrl+n` (Run) and `v` (Review). Setup's and the run
     screen's own `v` stay, and call `app.open_review(request, model)`.
   - **`open_review`.** It does `remove_mode("review")`, then
     `add_mode("review", lambda: ReviewScreen(…))`, then `switch_mode("review")`, and remembers the mode it
     came from.
   - **Review's `b`.** It switches back to that mode.
   - **The plain Review mode.** It is built from `app.tree` and the model:
     `ModelSpec(answers.model)`, else the settings model, else `None`.
   - **Workers in the right mode.** Setup's `_run` worker pushes the plan and run screens into the `run` mode
     even when another mode is showing: it switches to `run` first.
   - **Holding a run in tests.** `FakeGateway` gets an optional `hold: asyncio.Event`, awaited in `translate`, so
     that a test can keep a run going.
   - → check: Pilot tests:
     - a held run, `ctrl+o` shows Home, `ctrl+n` shows the same `RunScreen` with its progress, then the event is
       released and the run ends with its receipt;
     - from the run's receipt, `v` opens Review with the run's model, so retry is on, and `b` goes back to Run;
     - `v` from Home opens Review on Home's tree with the answers' model.

7. **`HomeScreen`** in `cli/tui/home.py` (ticket decision 005, story decision 005).
   - **Its data.** `ScanLocaleTreeQuery(app.tree, targets)`, where `targets` is the scan's `existing` without
     the source. That takes a first scan with no targets, as setup does. Then `ListFallbacksQuery(app.tree)`.
   - **The cards.** A cell's coverage is reusable ÷ (reusable + to_translate). The cards are:
     - COVERAGE, over all cells;
     - MESSAGES, the source's messages in its qualified files;
     - FALLBACKS, amber when there are any;
     - LOCALES, the codes and the source.
   - **The heatmap.** Each fallback is matched to its cell by `entry.file` against the cell's `path` relative to
     the scan's `output`, together with `entry.key` against `bundle_key`.
   - **The banner** leads to `v`.
   - **Empty states:**
     - no tree: "No locale tree found here · ctrl+n to set one up";
     - `SourceLocaleUnknown`: "Pick its source in a new run";
     - a refusal is shown as a notice.
   - **Reloads.** Home reloads on `screen_resume` and when the tree changes.
   - → check: Pilot tests on `examples/i18next`:
     - the four cards and every heatmap cell show the literal values counted once by hand from the example's
       files;
     - after writing a record with one fallback (as the review tests do with `RECORD`), the cell shows "◐ 1"
       and the banner says 1;
     - in an empty directory, Home shows the no-tree state.

8. **The tree switcher** (story decision 005, ticket decision 004).
   - It's a compact `Select` in the command bar, holding `app.trees`. It shows only when there are two or more
     trees.
   - Changing it sets `app.tree`, reloads Home, and rebuilds the Review mode with the same `remove_mode` /
     `add_mode`, unless Review is the current mode. In that case it replaces its screen.
   - When the `run` mode's stack is only its `SetupScreen`, it sets that setup's `#tree`.
   - A `RunScreen` going on keeps its own tree in its status line.
   - → check: a Pilot test on a copy of `examples/`, where several trees are detected. Switching changes
     Home's LOCALES card and the setup's `#tree`. With a held run, the run's status line keeps its tree.

9. **The snapshots** (story decision 006, ticket decision 001). `tests/tui/test_snapshots.py` covers:
   - Home on `examples/i18next` at 160×45 and 80×24;
   - Home with one fallback at 160×45;
   - setup in the shell at 160×45 and 80×24, with its old body until GH-69;
   - the small-terminal notice at 70×20.
   - → check: write them with `--snapshot-update`. Open each SVG and compare it by eye with v2's Home
     (https://claude.ai/artifact/4YxKpWHpFawQL6crNdD1nF). Then run them twice without the flag, and they pass.

10. **The docs.**
    - "Just run it" in `docs/guide/getting-started.md` changes to say:
      - `i18n-ai` opens on Home (the cards, the heatmap, the banner);
      - the sidebar and its keys (`ctrl+o`, `ctrl+n`, `v`);
      - the tree switcher.
    - The setup paragraph follows from there.
    - `docs/guide/tui.svg` becomes the Home snapshot at 160×45.
    - → check: `uv run --group docs sphinx-build -W -b dirhtml docs docs/_build/html` builds with no warning.

11. **The whole suite.**
    - → check: `uv run pytest` (coverage ≥ 85%), `uv run mypy`, `uv run ruff check` and
      `uv run ruff format --check`, `uv run lint-imports`.
    - `uv build`, then `unzip -l dist/*.whl | grep aurora.tcss` lists the stylesheet.

## Tests

- **Pilot, in `tests/tui/`:**
  - the theme and its palette (step 2);
  - the shell at three sizes (4);
  - the existing 30 tests inside the shell (5);
  - the modes, keys and a held run (6);
  - Home's values and empty states (7);
  - the switcher (8).
- **Unit:** `shade` (step 3).
- **Snapshots,** in `tests/tui/test_snapshots.py`, at 160×45 and 80×24 (step 9).
- **Expected values** are literals counted from the `examples/` files, never recomputed the way Home computes
  them.

## Risks

- **A worker pushing into the wrong mode.** `push_screen` pushes onto the current mode's stack, so setup's `_run`
  worker would put the plan on Home if the person switched away while the scan ran. It switches to `run` first
  (step 6), and a test plans, then presses `ctrl+o` before the plan shows.
- **Progress for a screen in a mode that isn't showing.** `TuiProgress` posts to the `RunScreen` while Home is
  shown. Step 6's held-run test proves that the screen still takes its events and is up to date on return.
- **Snapshots that never match twice.** This could come from temporary paths in the shown tree, or ids that
  change between runs. Step 1 proves determinism first. The trees are shown relative to the project, as setup
  does.
- **The 80-column tests.** The sidebar and command bar take room from setup's fields. At 80 columns the rail is
  narrow by design (story decision 002), and step 5 re-runs those tests.
- **The stylesheet not packaged.** `uv_build` ships the module directory's files, and step 11 checks the wheel.
- **Bindings clashing.** The app-level `v` sits under the screen-level `v` of setup and run, which call the same
  `open_review`. A text field with focus takes `v` as a letter, which is the reason for decision 006's choice.

## Corrections while building (2026-11-10)

- **`app.tree` is `app.locale_tree`.** `tree` is already a property on every Textual DOM node.
- **No `KeyHints` widget.** The status line's compact `Footer` shows the keys, so step 3 has no use for one.
- **The shell's handlers are `@on(...)` methods,** not `on_mount` / `on_resize`, so that a screen's own
  `on_mount` doesn't replace them.
- **`Trees.request(tree, shown, last)`** adds the source and output picked for that tree last time. This way Home
  and Review read the same fallback record as the setup.
- **The older tests open Run first**, with a `running` helper, since the app opens on Home. `fallen` and the
  `Snap` type moved into `tests/support/tui.py` with the other helpers.
- **The theme test reads `get_system_commands`** rather than typing into the palette.
- **`docs/guide/tui.svg` is the Home snapshot with one fallback,** so the docs show the banner too.
- **Review keeps the sidebar's count current** when it's on Home's tree, and `v` does nothing when the project
  has no tree.
