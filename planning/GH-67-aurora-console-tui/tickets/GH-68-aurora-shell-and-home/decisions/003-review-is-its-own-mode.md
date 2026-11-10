# 003: Review is a mode of its own, on Home's tree and the last model

**Date:** 2026-11-10 (ticket pass, Q3; agreed: "ok", to the recommended option 1)

**Question:** what does the Review section open from the sidebar, when today `ReviewScreen` is always pushed with
the setup's tree and model?

**Found:** `ReviewScreen(mediator, tree, model, options)` already takes `model=None` (retry off, a hint says to pick
a model); the saved answers keep `model`.

**Decision:** **Review is its own mode,** on the tree Home shows, with the saved answers' model, else the settings'
model, else none. When the setup or a finished run opens the review, the app switches to the Review mode and
replaces its screen with one on that run's tree and model, so a retry uses the model just picked. The sidebar's
Review entry shows the fallback count.

- **Why:** the review never covers a run being watched (story decision 004), and a retry from the sidebar works
  whenever a model is known.
- **Not chosen:** no Review mode, the review pushed in Run as today (it covers the run); Review always without a
  model (no retry from the sidebar).
