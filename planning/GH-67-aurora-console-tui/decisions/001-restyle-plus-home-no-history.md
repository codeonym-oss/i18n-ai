# 001: Every screen restyled as v2, plus a Home built from the tree; run history waits

**Date:** 2026-11-10 (grilling, Q1; agreed: "ok", to the recommended option 3)

**Question:** how much of the v2 "Aurora Console" design does this story ship?

**Decision:** **the v2 look on every screen there is, plus a Home screen built from what exists.**

- The app shell: the sidebar, the top command bar (`Ctrl+P`), the status line coloured by mode.
- The setup wizard, the plan, run and review screens, and the command palette, in v2's design.
- **Home:** the locale KPIs, the coverage heatmap and the fallback banner, all worked out from the tree's scan and
  the fallback record.
- **Not in this story:** anything that needs a record of past runs or new data: recent runs, the History page, KPI
  sparklines, the run's time-left estimate and throughput sparkline, per-call swim lanes, "same key elsewhere"
  beyond what the tree already holds, the Providers and Settings pages. They make a later story.

- **Why:** the app feel (shell, Home, palette, every screen) without a new history store; what waits is one
  coherent piece, the run history and what reads it.
- **Not chosen:** all of v2 in one story (8–10 tickets, a new store before the look ships); the restyle alone
  (no Home, the screen that makes v2 feel like an app).
- **Design:** the v2 canvas, https://claude.ai/artifact/4YxKpWHpFawQL6crNdD1nF.
