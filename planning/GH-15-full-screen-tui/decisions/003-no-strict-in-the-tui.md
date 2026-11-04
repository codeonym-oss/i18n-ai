# 003: The TUI has no strict option

**Date:** 2026-10-26 (grilling, Q3; agreed: "ok", to the recommended option 1)

**Question:** what does `--strict` mean in the TUI, when a refused file never reaches the disk the review fixes
(decision 002)?

**Decision:** **the TUI offers no strict option.** In a reviewed run the person is the gate: every fallback is shown,
and fixed or accepted. `--strict` stays a CLI option, for CI and other runs nobody reviews.

- **Why:** one write path, nothing held in memory (decision 002); strict's purpose, never shipping a fallback
  unseen, is what the review does.
- **Not chosen:** holding refused files until the review clears them (the held path decision 002 rejected, for
  refused files only); writing them anyway and flagging them (strict would mean something else than in the CLI).
