# GH-71: implementation plan

Planned 2026-11-12 against `main` at 9e3e354. Ticket decisions 001–006 (006 supersedes part of 003 and 005); story decisions 001–006 (one look in
`aurora.tcss` and `kit/`, breakpoints, snapshots at 160×45 and 80×24, nothing new underneath); #15 decision 004
(typed progress events); GH-70 decisions 003 and 005 (the scrolling grid, its labels fixed).

## Read first

- `src/i18n_ai/cli/tui/run.py`: `RunScreen`, its events (`on_tui_progress_event`), `show_receipt`, `stopped`,
  `done`, `reviewable`, `check_action`.
- `src/i18n_ai/cli/tui/grid.py`: `JobGrid`, used by the run screen alone; it goes.
- `src/i18n_ai/cli/tui/plan.py`: the grid in `body` (`#grid-top`, `#locale-strip`, `#grid-body`, `#file-column`,
  `#cells`), `_locale_heads`, `_file_heads`, `_columns`, the scroll watchers, `_moved`, `count`.
- `src/i18n_ai/cli/tui/kit/widgets.py`: `PlanCell` (arrows, `Moved`), `Card`, `KpiTile`.
- `src/i18n_ai/cli/tui/aurora.tcss`: "Plan cells", "The plan's headers and run bar".
- `src/i18n_ai/cli/tui/setup.py` `_run` (≈ line 725): pushes the run, sends the command, `stopped` on a refusal,
  `show_receipt` with the command again, the note and the review.
- `src/i18n_ai/cli/tui/app.py`: the run's palette commands, `workers.cancel_all` on quit.
- `src/i18n_ai/application/ports/progress/events.py` and `result.py`: the events and `FileResult`.
- `src/i18n_ai/application/intents/locale/commands/generate_locales/handler.py` ≈ 160–211: the record written in a
  `finally` (decision 004 rests on it).
- Tests: `tests/tui/test_tui.py` (the run tests: `cells`, `text`, `showing`, the retry test patching
  `JobGrid.show`), `tests/tui/test_plan.py` (`receipt`, the row-off test reading the run's `DataTable`),
  `tests/tui/test_shell.py` (a held run), `tests/support/tui.py` (`ended`), `tests/tui/test_snapshots.py`.

## The design, point by point

- **The grid** (decision 001): `kit/grid.py` gets `CellGrid`, the plan's grid lifted out: the corner, the locale
  headers and the file names held fixed while `#cells` scrolls, the columns at `CELL_WIDTH` at the least. It takes
  the files, the locales with their names, the file notes and the cells; it keeps the heads in step with the scroll
  and moves the focus on a cell's `Moved` (the plan's `_moved`). `PlanScreen` uses it; its look stays the same
  (its snapshots do not change).
- **The cells:** `GridCell(Vertical, can_focus=True)` in `kit/widgets.py` holds the arrows and `Moved`; `PlanCell`
  and a new `RunCell` derive from it. `RunCell.show(state, detail)` with state `waiting`, `translating`, `retry`,
  `written`, `partial`, `refused`, `failed`, `ignored`, `stopped` or `off`: a glyph and its word in the tag
  (◌ ▸ ⟳ ● ◐ ✕), the detail on the next line (`attempt 2/3`, `12 translated · 26 kept`, `1 fallback`, the reason),
  `text` as the tests read it (`written`, `retry 2/3`). The state tints are in `aurora.tcss`, as the plan cells'.
- **The progress card** (decision 002): `#progress`, a `Card`: DONE `64%`, a strip by message (mint written,
  amber partial or refused, coral failed, dark still to come; `heat.py` gets a `progress(width, written, partial,
  failed, total)` beside `strip`), and the line `7/11 jobs · 129/201 messages · ⟳ 3 ◐ 1 ✕ 0 · 00:42`. A cell's
  planned messages are its `to_translate` in the report; a job counts them when it ends. `FileDropped` takes its
  jobs and messages out of the totals. Narrow: one line, as the plan's run bar.
- **The clock:** `RunScreen(..., clock=time.monotonic)`; a one-second interval redraws the time while it runs; it
  stops at the end. The status line reads `RUNNING · 7/11 jobs · 00:42` then the tree.
- **The feed** (decision 003): `#events`, a `Card` holding a `Log`-like list (newest on top; a `VerticalScroll` of
  `Static` lines, so the line's glyph keeps its colour), one line per event as decision 003 writes them, and
  under a done job's line what decision 006 adds: a sub-line per fallen-back key with its reason and per warning,
  eight each then `… and N more` (the CLI's `_LISTED`, shared rather than copied), and the written path at the
  end of a written line (`shown(path)`, as `render_receipt`). `p` switches all / problems, the reasons and
  warnings kept; the card's title says which. A partial, failed or refused job, a dropped file and the end
  notify. Wide: beside the grid, 44 columns; narrow: under it, at most 6 lines.
- **Stop** (decision 004): `Binding("ctrl+c", "stop", "Stop")` shown while it runs. `SetupScreen._run` runs in a
  worker; the run screen keeps a `stop: Callable[[], None]` that the setup gives it (the worker's `cancel`). On
  `CancelledError` in `_run`, the screen's `stopped_by_hand()`: unfinished cells read `stopped`, the feed and a
  notice `■ stopped · 7 of 11 jobs done`, the "Run it again" card with the command; no tiles.
- **The end** (decision 005): `show_receipt(receipt, again, note, review)` swaps `#progress` for four `KpiTile`s
  (FILES WRITTEN, TRANSLATED, FALLBACKS, FAILED, the counts from `receipt.results`), and shows `#again`, a `Card`
  "Run it again": `$ <command>`, the note, `y copy · v review N fallbacks`. `y` calls
  `self.app.copy_to_clipboard(again)` and notifies. The column heads show each locale's written / jobs. Rich's
  receipt is no longer printed in the TUI (`render_receipt` stays for the CLI). `stopped(reason)` (a refusal)
  keeps its red line, in the `#again` card's place.
- **Unchanged:** `done`, `reviewable`, Back once over, the palette commands, `TuiProgress`, the setup's command
  line and note.

## Steps

1. **`GridCell` and `CellGrid` from the plan.** Lift the arrows and `Moved` into `GridCell`; move the grid's
   compose, `_columns`, the heads, the scroll watchers and `_moved` into `kit/grid.py` `CellGrid`; `PlanScreen`
   composes a `CellGrid` with its `PlanCell`s. → check: `tests/tui/test_plan.py` and the plan snapshots pass
   unchanged.
2. **`RunCell`.** Its states, glyphs, detail and `text`; tints in `aurora.tcss` ("Run cells").
   → check: a unit test of `RunCell.show` in `tests/tui/test_run.py` mounting one cell: each state's tag and text.
3. **The run screen's grid.** `RunScreen` composes a `CellGrid` of `RunCell`s (off cells `off`, the rest
   `waiting`); the events drive the cells as `JobGrid.show` did; `grid.py` and `JobGrid` go. Move the run tests
   to `tests/tui/test_run.py`, `cells()` reading `RunCell.text`, the retry test patching `RunCell.show`.
   → check: the moved tests pass (a retry reads `translating`, `retry 2/3`, `written`; waiting then written; the
   cells off).
4. **The progress card and the clock.** `heat.progress`, the totals by message, the jobs, the ⟳ ◐ ✕ counts, a
   dropped file out of the totals, the clock injected. → check: tests: halfway through a held run the card reads
   its jobs and messages; a partial run's `◐ 1`; `heat.progress` cases in `test_heat.py`.
5. **The feed and the pop-ups.** The lines, newest first, the `p` switch, the notifications.
   → check: tests: a retry's line `⟳ 1 message sent back · attempt 2/3`; a partial's `◐ partial · 1 fallback`,
   its sub-line `app.welcome · <reason>` and its notification; a written line ending on
   `locales/fr/common.json`; a job with a warning shows `! 1 warning` and it (the fake gateway made to give one);
   `p` leaves only the problem lines with their reasons (replaces the Problems test).
6. **The end.** The tiles, the "Run it again" card, `y`, the column heads' counts; `stopped(reason)` in its place.
   → check: the receipt tests read `#again` (`To run it again`, the single-cell note, `--exclude common.json`);
   the tiles' figures for a run with one fallback; `y` puts the command on the app's clipboard
   (`app.clipboard`); Review and Back as before.
7. **Stop.** `ctrl+c` while running, the setup's cancel, `stopped_by_hand`. → check: a test holding the fake
   model (`gateway.hold`): one job done, `ctrl+c`; its target is written, the others read `stopped`, the feed
   says `stopped · 1 of 2 jobs done`, `ctrl+c` is gone from the footer, Back works, a fresh run goes again.
8. **The layout at both sizes.** Wide: progress over the grid, the feed beside; narrow: one-line progress, the
   feed under the grid. → check: a test at 80×24: the grid, the feed, the progress and the footer fit, the grid
   scrolls to the last locale with its heads.
9. **Snapshots.** `tests/tui/test_snapshots.py`: a `RunScreen` pushed on its own, on the report the setup scans,
   the clock fixed, a scripted series of events posted (started, a retry, a written, a partial with its pop-up):
   `test_run[160x45]`, `test_run[80x24]`; and `test_run_ended` (the receipt, 160×45). → check: the SVGs looked
   at, then written with `--snapshot-update`.
10. **Docs.** `docs/guide/getting-started.md`: the run paragraph (≈ line 62: the bar and **Problems** become the
    progress card, the feed and `p`, the pop-ups, `ctrl+c`, the receipt's tiles and `y`), and
    `docs/guide/tui-run.svg`, a copy of the 160×45 snapshot, under it as the plan has `tui-plan.svg`.
    → check: `sphinx-build -W` passes.
11. **Every check.** ruff, format, mypy, lint-imports, sphinx, the whole suite.

## Tests

- **Pilot, `tests/tui/test_run.py`:** the cells follow their jobs (waiting, translating, retry, written, partial,
  off); the progress card's figures; the feed's lines and `p`; the pop-ups; the end's tiles and "Run it again",
  `y`; stop; 80×24. On the real flow (setup → plan → run) with the fake model, `gateway.hold` or `broken_first`
  where a state must be caught.
- **Unit:** `RunCell.show`, `heat.progress`.
- **Snapshots:** the run mid-way at 160×45 and 80×24, and ended, on scripted events with a fixed clock.

## Risks

- **Lifting the grid out of the plan** could shift the plan's look: its three snapshots must pass unchanged
  (step 1 checks it before anything else moves).
- **`ctrl+c`** is Textual's `help_quit`: the run screen's binding takes it while it runs; when over, the app's
  comes back. A test checks both.
- **Cancelling `_run`** must not leave `self._progress.target` set (the `finally` clears it) nor count as a
  refusal; the record is the handler's `finally`.
- **A one-second interval** could make snapshots or tests flaky: the clock is injected and fixed in snapshots;
  tests read figures, not the time.
- **Many notifications** on a run with many partial jobs: Textual stacks them and times them out; accepted.
- **`app.clipboard`** in tests holds what `copy_to_clipboard` was given (the terminal is not touched).

## Corrections while building

- **`stopped_by_hand()` is `halted(again, note)`:** the setup works the command out before the run starts, so a
  stop can show it; `halted` does nothing when the screen is gone (the app quitting mid-run cancels the worker
  too).
- **The engine only translates;** every write is the handler's, in its loop. A cancelled run writes nothing more,
  which decision 004 needed (checked in `infra/adapters/langgraph/engine.py`).
- **`CellGrid.cell` returns None** for a file or locale the grid lacks: a file added since the plan is translated
  and in the feed, with no cell (as `JobGrid.show` ignored it).
- **The progress card's inner `Vertical`s need `height: auto`,** or the card takes the whole column.
- **The feed's height is set in `_fit`** (`1fr` beside the grid, 8 lines under it): the app's `.card { height:
  auto }` outranks a screen's `DEFAULT_CSS`.
- **Pop-ups in snapshots:** Textual's `run_test` leaves notifications out; the `snap` fixture takes
  `notifications=True`, used by the run's snapshots only.
- **`FakeGateway.unchanged`:** keys given back as their source, so a test has a warning to show.
- **The narrow status line** leaves out `RUNNING ·` (the section's chip says it), so the keys fit at 80 columns.

## After the review

Fixed: an event for a cell the grid lacks no longer raises; the column heads count the files written of their
jobs, a dropped file's leaving; a failed job lists its fallen-back keys too; narrow, the bar and its line share
one line; the status line says `RUNNING`; a refused run pops up; one `PARTLY` for the partial-like states and
`STATE_OF` for the status map; `RunCell.show`'s docstring. Tests added: `◐ 1`, the failed, finished and stopped
pop-ups, a file outside the grid, a fresh run after a stop, the one-line card at 80×24.

Kept as built: the notes map built by both screens and `_listed` beside the CLI's own (small; sharing them would
reach into the CLI's renderer); `left` beside `review` on `show_receipt`; the `∅` glyph for ignored, the
"N to translate" detail on waiting cells, the narrow tiles two by two; the stop line in the feed's two-line shape
(`■ stopped` / `1 of 2 jobs done`); the column heads updating as the run goes.

Found, not fixed (follow-up `key-clears-the-picked-model`, updated): a key typed for a run clears the picked
model, so Back finds no model.

**After the pull request opened (a side agent's note):** `y` goes through Textual's `copy_to_clipboard`, an OSC 52
request the terminal may ignore (GNOME Terminal, macOS Terminal, tmux without its setting), and the app cannot tell.
The notice no longer says the command is copied: it says the terminal was asked, and points to the command on
screen. The guide says the same.
