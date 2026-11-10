# 004: The tree switcher moves everything but a run going

**Date:** 2026-11-10 (ticket pass, Q4; agreed: "ok", to the recommended option 1)

**Question:** what does the command bar's tree switcher (story decision 005) do while the Run mode is generating?

**Decision:** **it moves Home, the Review mode and the tree a new setup starts on; a run going keeps its tree.**
That run's status line names its tree, so it reads as another one. When the Run mode is on its setup form with no
run going, the form moves to the new tree.

- **Why:** a run is bound to the tree it started on, as in the CLI; the switcher is for looking.
- **Not chosen:** the switcher disabled during a run (no look at another tree meanwhile); a switch that asks to
  cancel the run (throws work away for a glance).
