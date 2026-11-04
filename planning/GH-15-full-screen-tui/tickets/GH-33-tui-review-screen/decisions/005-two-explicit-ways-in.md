# 005: Two explicit ways into the review; retry uses the form's model

**Date:** 2026-11-04 (ticket pass, Q5; agreed: "1, go with your recommendation")

**Question:** how does the person reach the review screen, after a run and from the TUI's start, and where does
retry get its model?

**Decision:** **an explicit `v` binding at both places, and retry uses the setup form's provider and model.**

- **After a run:** when fallbacks remain, the run screen's receipt gets **Review** (`v`) beside **Back**; the
  receipt is read first.
- **From the start:** once the setup has scanned a tree, a line under it says how many fallbacks are recorded
  (`ListFallbacksQuery`), with **Review** (`v`); none recorded, no line and no binding.
- **Retry** sends the form's model. With no model picked yet, retry is off and says why; edit and accept work.

- **Why:** the receipt keeps its place as the run's summary; both ways in have a key binding (story rule) and show
  only when there is something to review.
- **Not chosen:** opening the review by itself after a run (skips the receipt); the palette only (hidden, and
  against the story's key-binding rule).
