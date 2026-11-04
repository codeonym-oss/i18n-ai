# 006: Retry and accept act on the marked rows, or the highlighted one

**Date:** 2026-11-04 (ticket pass, Q6; agreed: "1, go with your recommendation")

**Question:** do retry and accept act on one row of the review, or on several?

**Decision:** **`space` marks a row; `r` and `a` act on the marked rows, or on the highlighted row when none is
marked.** Edit (`e`) is always the highlighted row. One retry sends one job per file × locale, however many of its
rows are marked.

- **Why:** fixing many fallbacks of one kind is one action and few model calls; `space` toggles as on the plan
  screen.
- **Not chosen:** the highlighted row only (one model call per fallback); "all" bindings (no subset, and one key
  accepts the whole tree).
