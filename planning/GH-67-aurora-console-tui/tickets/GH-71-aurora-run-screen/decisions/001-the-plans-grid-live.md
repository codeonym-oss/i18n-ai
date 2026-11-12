# 001: The run's main panel is the plan's grid, live

**Date:** 2026-11-12 (ticket pass, Q1; agreed: "ok 1")

**Question:** with v2's lanes out (story decision 001), what is the run screen's main panel?

**Decision:** **the plan's files × locales grid, each cell a job card that follows its job.** The same fixed file
and locale labels and the same scrolling as the plan (GH-70 decisions 003 and 005). A card shows its state as a glyph
and a word (◌ waiting, ▸ translating, ⟳ retry 2/3, ● written, ◐ partial, ✕ failed, ignored, — off), its attempts,
and once done its translated and kept counts. The progress card sits above it, the events feed beside it.

- **How:** a `RunCell` in `kit/` beside `PlanCell`, and the plan's grid layout shared by both screens; `JobGrid`,
  used by the run screen alone, goes.
- **Why:** "each job as a card" of the draft; the grid keeps its place from plan to run, and fits 80×24 as the
  plan does.
- **Not chosen:** v2's file rows of glyphs (no attempts or counts per job, unreadable with many locales); the events
  feed alone (no state at a glance).
