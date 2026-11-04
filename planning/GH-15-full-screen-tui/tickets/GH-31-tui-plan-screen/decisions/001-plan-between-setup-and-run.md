# 001: Setup leads to the plan; the plan's Run is the go-ahead

**Date:** 2026-10-29 (ticket pass, Q1; agreed: "1")

**Question:** where does the plan screen sit between the setup and the run?

**Decision:** **always setup → plan → run.** The setup's button becomes **Plan** (`ctrl+r`): it gives a typed key,
asks before installing a missing provider package, remembers the answers, then opens the plan. The plan screen's
**Run** (`ctrl+r`) starts the generation, with no confirmation after it; **b** or escape goes back to the form.
This changes GH-30's decision 004 in one point only: the go-ahead moves from the setup to the plan. The install
dialog, the run screen and the receipt with its command line stay as 004 has them.

- **Why:** the issue puts the plan "between setup and run"; the go-ahead stays one press, on the screen that shows
  exactly what will run.
- **Not chosen:** the plan only when asked, beside a Run that skips it (two ways to start, the grid easy to miss);
  the grid under the setup form (crowds 80×24, as GH-30's decision 003 found).
