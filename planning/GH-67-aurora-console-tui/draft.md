# Redesign the TUI as the Aurora Console

## Goal

The TUI (#15) works, but its screens use Textual's stock look: plain tables and forms that read as generic, and
nothing to see before a run is set up. This story redraws it as an app, the "Aurora Console" of the v2 design:
a sidebar, a command bar, a status line, a Home dashboard, and every screen rebuilt on one theme and one set of
widgets.

Design (v2): https://claude.ai/artifact/4YxKpWHpFawQL6crNdD1nF

## What it delivers

- **The shell:** a sidebar with Home, Run and Review, each keeping its own place (a run goes on while you look at
  Home); a top command bar with `Ctrl+P` and a tree switcher; a status line coloured by mode (decision 004).
- **Home:** the tree's locales as KPI cards, a files × locales coverage heatmap, and a banner for the recorded
  fallbacks, all from the scan and the fallback record (decisions 001, 005).
- **Setup** as a wizard with locale cards and toggles; **Plan** as big cells with their message strips and an
  inspector; **Run** with its progress, its events and pop-up notices; **Review** as a three-way comparison
  (source, rejected translation, your edit) with the attempts.
- **The command palette:** `>` for commands, `@` for locales, `#` for files.
- **Any terminal:** the full layout from about 120 columns; narrower, an icon rail and stacked panels; below
  80×24, a notice (decision 002).

## Rules every ticket keeps

- **One look:** colours come from the `aurora` theme, shared rules from `cli/tui/aurora.tcss`, shared widgets from
  `cli/tui/kit/`; a screen holds only its own layout CSS (decision 003).
- **Nothing new underneath:** the screens send the same queries and commands as today; no ticket adds a query, a
  command or a store. The #15 decisions hold: the run writes as it goes, the review fixes what is on disk, no
  strict option, cells off through the skip set.
- **The app always runs:** after each ticket the whole flow works; a screen not yet redone keeps its old look
  inside the new shell.
- **Tests:** each screen keeps its `Pilot` tests for what it does, and gains SVG snapshots at 160×45 and 80×24
  (`pytest-textual-snapshot`, decision 006).
- **Layers:** `textual` stays inside `i18n_ai.cli.tui`.

## Tickets, in the order they ship

1. **The Aurora shell, theme and Home** (decisions 002–006): the frame every other ticket builds on.
2. **The setup wizard.**
3. **The plan screen.**
4. **The run screen.**
5. **The review screen.**
6. **The command palette** (decision 007 for the order).

## Not part of it

- **Run history and what reads it** (decision 001): recent runs, the History page, KPI sparklines, the run's time
  left and throughput, per-call swim lanes. A later story, with a store of past runs.
- **The Providers and Settings pages** of the sidebar (decision 001).
- **A light theme** (decision 003).

## Done when

- [ ] `i18n-ai` opens on Home, and a run on an `examples/` tree with the fake model goes from setup through plan
      and run to review in the new look.
- [ ] Every screen has snapshots at 160×45 and 80×24, and its `Pilot` tests pass.
- [ ] No screen uses a colour that is not in the `aurora` theme.
