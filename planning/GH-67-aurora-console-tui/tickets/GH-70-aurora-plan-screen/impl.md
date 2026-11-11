# Implementation: show a TUI run's plan as Aurora cells with an inspector

Planned 2026-11-11 against `main` at 6975810. Story decisions 001–007, ticket decisions 001–004; GH-15 decision 005
(cells off through the skip set).

## Read first

- `src/i18n_ai/cli/tui/plan.py`: `PlanScreen` on `JobGrid` today.
  - `__init__` (`_files`, `_targets`, `_cells`, `_left_out`, `_off`), `_label`, `_total`, `_toggle`;
  - `action_cell`, `action_row`, `action_column`, `action_run`, `action_back`: what they do stays;
  - `count`, which `setup.py` imports too.
- `src/i18n_ai/cli/tui/grid.py`: `JobGrid`. The plan stops using it; the run screen keeps it until GH-71.
- `src/i18n_ai/cli/tui/setup.py`, `_run`: it sends `ScanLocaleTreeQuery` and pushes `PlanScreen(report)`; it holds
  the request, and `self._settings` with the batch size (`generation_options`).
- `src/i18n_ai/application/intents/locale/queries/scan_locale_tree/view.py`: `TargetFileView` (`exists`,
  `to_translate`, `reusable`, `path`), `SourceFileView` (`qualifies`, `reason`, `messages`). Recorded fallbacks are
  counted in `to_translate`, not in `reusable` (the handler's docstring).
- `src/i18n_ai/application/intents/locale/queries/list_fallbacks/view.py`: `FallbackView` (`ref.file`,
  `ref.target`, `ref.path`, `source`, `stale`).
- `src/i18n_ai/infra/adapters/langgraph/atom.py`, `translate`: an atom's messages go in batches of `batch_size`.
- `src/i18n_ai/cli/tui/kit/widgets.py` (`Card`, `Chip`, `LocaleCard` as the pattern of a focusable kit widget),
  `kit/shell.py` (`ShellScreen`, `WIDE`, `-narrow`, `#crumb`, `#status-tree`), `aurora.tcss`.
- `src/i18n_ai/cli/tui/app.py`, `get_system_commands`: the plan's Run command.
- Tests: `tests/tui/test_tui.py` lines 31–45 (`cells`, `total`, `on_cell`) and 234–372 (the plan's tests);
  `tests/support/tui.py` (`planning`, `ready`); `tests/tui/test_snapshots.py`.
- `docs/guide/getting-started.md`, "Just run it" (its plan paragraph) and `docs/guide/tui-plan.svg`.

## The design, point by point

`v2/Plan` of https://claude.ai/artifact/4YxKpWHpFawQL6crNdD1nF (version 1794384556-a439, read again 2026-11-11),
as far as decisions 001–004 keep it. Each point is checked against the snapshots in step 8.

- **Command bar:** the crumb reads "New run / Plan". On the right, muted, "nothing sent to a model yet", and the
  primary button "▶ Run 4 agents ⌃R". v2's Grid / Messages / Tree switcher is left out (decision 001).
- **Grid card:** a header row "FILE ╲ LOCALE", then a chip per locale: the code in bold violet, the name muted,
  its messages to translate on the right. A row per file: its name in bold, "38 messages" muted under it.
- **A cell** (decision 003): a tag (NEW sky, FILL amber, UP TO DATE mint, OFF muted) and the mark ■ (violet) or □
  (muted) on the right; the number of messages to translate in bold, "✓" in mint when up to date, "—" when off;
  the strip under it (decision 002). Its border and background tinted by its state, dashed and muted when off; the
  focused cell has a heavy violet border.
- **The strip** (decision 002): the cell's width is the file's messages; sky for the ones to translate, amber for
  its recorded fallbacks, dark for the kept ones; muted when the cell is off.
- **Under the grid:** the legend, "█ to translate · █ kept · █ fallback again", and on the right the dashed note
  "left out · meta.json — it looks like data", one per file left out.
- **Inspector** (decision 001): a card titled "INSPECTOR" with "common.json → de" on the right; the state and the
  counts ("fill · 13 to translate · 2 kept"), the target path, then the recorded fallbacks, each its key in bold, a
  FALLBACK tag, and its source text muted on one line. With none, "no recorded fallback". Beside the grid from 120
  columns, under it below (story decision 002).
- **The run bar** (decision 004): "THE RUN", then "47 messages · 4 agents · 5 calls of ≤40", and on the right "a
  cell space · row r · column c". v2's lanes are left out (story decision 001).
- **Status line:** "plan" as the mode, then "3 of 4 cells on · common.json → de off" (the first cells off, then
  "+N more").
- **Keys:** the arrows move between cells, Space / `r` / `c` toggle, ⌃R runs, Esc goes back. A click focuses a
  cell; the inspector follows the focus, so ⏎ is not bound.

## Steps

1. **`PlanCell` in the kit** (`kit/widgets.py`, CSS in `aurora.tcss`): a focusable `Vertical` holding the file, the
   locale, and a `show(state, number, strip)` that draws the tag, the mark, the number and the strip, with the
   state as a class (`-new`, `-fill`, `-done`, `-off`). It posts no message of its own: the screen learns of the
   focus through Textual's `DescendantFocus`. Short at `-narrow` (the tag and the number on one line).
   → check: a test in `tests/tui/test_plan.py` mounting a plan shows each cell's tag and number, and the focused
   cell has the `:focus` border (snapshot, step 8).
2. **The strip** as a function in `kit/heat.py`: `strip(width, to_translate, fallbacks, total) -> Content`, the
   runs in proportion, at least one cell of a run that is not zero, the fallbacks inside the sky run.
   → check: unit tests in `tests/tui/test_heat.py`: 10 of 20 at width 10 is 5 sky and 5 dark; 1 of 400 is one
   sky cell; 3 fallbacks of 10 to translate show amber; all kept is all dark.
3. **`PlanScreen`'s body** rebuilt: the grid card (header chips, the rows of `PlanCell` in a `Grid` inside a
   `ScrollableContainer`), the legend and the left-out notes, the inspector card, the run bar. `_label` becomes
   `_state(file, locale)`, used by the cells and the inspector. `PlanScreen(report, fallbacks, batch)`: the setup
   sends `ListFallbacksQuery(request)` before it pushes the plan (a refusal: no fallbacks) and passes the batch size
   from its settings. The fallbacks are kept per (file, locale) from `ref`, stale ones dropped.
   → check: `test_the_plan_shows_each_file_and_locale` rewritten on the cells: auth/login.json new 10, new 9;
   common.json fill 13, new 15; "Left out: meta.json" in the note.
4. **Moving between cells:** the arrows bound on the screen move the focus to the neighbour cell (clamped at the
   edges), `scroll_visible` on it; the first cell has the focus on mount. `action_cell`, `action_row` and
   `action_column` read the focused cell instead of `JobGrid.under_cursor`. A click focuses the cell.
   → check: a test pressing `right`, `down` lands on common.json → de; the carried-over
   `test_a_cell_a_row_or_a_column_turns_off`, with focus instead of the cursor, gives the same cells and totals.
5. **The inspector** follows the focus: on `DescendantFocus` from a `PlanCell`, it shows the cell's state, counts,
   path and fallbacks.
   → check: a test with one recorded fallback (the `fallen` helper) shows its key and FALLBACK in the inspector on
   its cell, and "no recorded fallback" on another; the cell's strip has the amber run (its `Content` spans).
6. **The run bar and the status line:** `_total` writes "N messages · N agents · N calls of ≤B" with the calls
   ⌈to_translate ÷ B⌉ over the cells on; the status line "N of M cells on" and the first cells off. The header's
   button reads "▶ Run N agents ⌃R" and runs on a click.
   → check: the totals in the carried-over tests ("47 messages · 4 agents · 4 calls of ≤40"; after a cell off,
   "32 messages · 3 agents · 3 calls of ≤40"), and the status line after one cell off.
7. **The rest of the plan's tests carried over** into `tests/tui/test_plan.py` (every cell off, a cell off is not
   written, a row off is excluded, 80 columns, a plan with no file takes its keys), the helpers rewritten on the
   cells; `test_tui.py` keeps `cells` for the run screen.
   → check: `uv run pytest tests/tui` passes.
8. **Snapshots:** `test_plan` at 160×45 and 80×24, with one cell off and one recorded fallback, focused on its
   cell. Look at both against "The design, point by point". `docs/guide/tui-plan.svg` becomes the 160×45 one, and the
   docs' plan paragraph says the cells, the inspector and the run bar.
   → check: `uv run pytest tests/tui/test_snapshots.py`, the PNGs looked at, `sphinx-build -W`.
9. **The whole suite and the checks:** `uv run pytest`, ruff, format, mypy, lint-imports.

## Tests

- **Pilot, at the screen** (`tests/tui/test_plan.py`): what the cells show, the focus moving, Space / `r` / `c`,
  the totals and the status line, the inspector with and without a fallback, every cell off, a cell off not
  written, a row off excluded, 80 columns, no file. All through the keys and what the widgets show.
- **Unit** (`tests/tui/test_heat.py`): the strip's runs.
- **Snapshots** (`tests/tui/test_snapshots.py`): the plan at 160×45 and 80×24.

## Risks

- **The setup's `_run` changes** (it sends `ListFallbacksQuery` and passes the batch size): the run and review tests
  in `test_tui.py` and `test_shell.py` cover it, unchanged.
- **Calls vs units:** an atom batches its schema's units, which may not be one per message for plurals in some
  formats. Checked in step 6 against a file with plurals; if they differ, the bar counts what `to_translate`
  counts and says so in "Corrections while building".
- **A big grid at 80×24:** many files or locales scroll; `test_the_plan_fits_80_columns` (five locales) checks the
  grid, the run bar and the footer stay inside the screen.
- **Focus and the footer:** the snapshot fixture waits for the footer (`footed`); a focus moved at mount is settled
  before the screenshot.
- **`count`** stays in `plan.py`, imported by the setup.

## Corrections while building

- **The arrows are the cell's bindings,** and `PlanCell` posts `Moved`: the scrolling view around the cells binds the
  arrows itself, and a binding of the focused widget comes before its ancestors'. Step 1's "posts no message" no
  longer holds.
- **The file names and the locale headers sit outside the cells' scrolling view** (decision 005): the header strip
  and the file column follow its `scroll_x` and `scroll_y`, with `force=True` since their own overflow is hidden.
  `test_the_plan_fits_80_columns` checks the header and the file stay aligned with the focused cell; a third
  snapshot, `test_plan_scrolled` at 80×24 on five locales, shows the grid scrolled to the last.
- **The snapshot fixture no longer settles after the setup step;** each step settles what it waits for. The plan is
  pushed from the setup's worker, which waits on it, so waiting for every worker never ended.
- **`.card.-fill` in `aurora.tcss`:** `aurora.tcss` is app CSS and outranks a screen's `DEFAULT_CSS` whatever the
  selector, so `.card { height: auto }` won over `#grid-card`. The grid card fills with `-fill`; the inspector is a
  plain bordered `Vertical`, so its height and violet border stay the screen's.
- **The header class is `.column-head`:** `.locale-head` is already the setup's locale cards'.
- **Narrow, the status line counts the cells on without naming the ones off;** they crowded the keys out of the
  footer at 80 columns.
- **Calls vs units (a risk):** the scan's `to_translate` is `len(schema.units) - reusable`, the units an atom
  batches, so the calls are exact for a first attempt.

### After the review

Fixed:

- **The plan's panel look is in `aurora.tcss`** (story rule "one look"): the inspector is a `Card` with `-accent`, and
  `-fill` beside the grid only; the locale headers' and the run bar's look moved there too.
- **The state's words are one map on `PlanCell`** (`WORDS`, `NUMBERS`), which the inspector reads.
- **The strip's runs are one list in `kit/heat.py`** (`RUNS`), drawn by `strip()` and named by `legend()`.
- **`strip()` clamps the fallbacks itself and keeps its width** when narrower than its runs (two unit tests).
- **The locale headers count the cells on**, and change as cells turn off.
- **The status line names the cells off in the grid's order.**
- **A file's row says "15 messages in en":** it counts the source file's messages, while a cell counts its target's
  units, which a locale with more plural forms makes more (common.json: 15 messages, 16 units in fr).

Kept as built:

- **The note and the Run button are in a row of the grid card,** not the command bar: the shell's command bar has no
  place for a screen's own widgets, and opening one is the command palette ticket's (GH-73) business.
- **The status line's chip says RUN:** it names the sidebar's section on every screen (story decision 004).
- **Narrow, the run bar stays under the grid and above the inspector:** it is the grid column's.
