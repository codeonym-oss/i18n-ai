# Open the TUI on the Aurora shell and its Home

## Problem

The TUI opens straight on a stock Textual form: no frame, no overview of the tree, and each screen styles itself.
Every later screen of the redesign needs a shared theme, shared widgets and a shell to sit in.

## The change

- **The look** (story decision 003): an `aurora` Textual theme with v2's tokens, `cli/tui/aurora.tcss` for the
  shared rules, and `cli/tui/kit/`: titled card, KPI tile, status chip, heat strip, key hints. Textual's stock
  themes are not offered.
- **The shell** (decision 004): the modes Home, Run (setup → plan → run, the screens as they are) and Review; the
  sidebar, the command bar (`Ctrl+P`, the tree switcher), the status line coloured by mode.
- **Home** (decisions 001, 005): the tree the setup would pick; its locales as KPI cards, a files × locales coverage
  heatmap (reusable ÷ (reusable + to translate)), the fallback banner leading to Review; an empty state pointing to
  New run when no tree is found.
- **Breakpoints** (decision 002): an icon rail and stacked panels below about 120 columns, a notice below 80×24.
- **Snapshots** (story decision 006, ticket decision 001): `syrupy` in the test dependencies and a fixture on
  Textual's `export_screenshot()` (the `pytest-textual-snapshot` plugin needs pytest below 9); Home's snapshots at
  both sizes.

Settled in the ticket pass: every screen is a `ShellScreen` filling its `body()` (decision 002); Review is a mode
of its own, on Home's tree and the last model (003); the tree switcher leaves a run going alone (004); Home's four
cards, heatmap and banner (005); `ctrl+o` Home, `ctrl+n` Run, `v` Review (006).

## Out of scope

- Restyling setup, plan, run, review and the palette (tickets 2–6); anything that needs run history.

## Done when

- [ ] `i18n-ai` at a terminal opens on Home for an `examples/` tree, with its KPIs, heatmap and fallback banner.
- [ ] A `Pilot` test leaves a run going, opens Home, returns, and finds the run still there.
- [ ] Home's snapshots at 160×45 and 80×24, and the small-terminal notice below 80×24.
- [ ] The existing TUI tests pass inside the new shell.
