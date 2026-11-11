# 005: The wizard opens on Targets once the tree is scanned, else on Tree

**Date:** 2026-11-11 (ticket pass, Q5; agreed: "ok", to the recommended option 1)

**Question:** which step does the wizard open on, when it always starts on a tree (story decision 005) and the last
answers often fill the rest?

**Decision:** **the first step that still needs something, Targets at the latest.**

- **Tree** when no tree was found (its path is typed) or the source has to be asked.
- Else **Targets**, even when the last answers fill every field: it is the step most often changed, and ⌃R plans
  from it at once.
- A tree changed with the switcher, or a source picked, leaves the step where it is.

- **Why:** no Continue past a tree Home already chose; the design's "step 2 of 3" is where a run usually starts.
- **Not chosen:** always Tree (one step too many on every run); where it was left last time (a field added to the
  saved answers, against the story's "nothing new underneath").
