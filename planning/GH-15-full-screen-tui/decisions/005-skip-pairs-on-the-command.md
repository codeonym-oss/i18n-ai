# 005: The plan's cells turn off through a skip set on the command

**Date:** 2026-10-26 (grilling, Q5; agreed: "ok", to the recommended option 1)

**Question:** how does turning off one file × locale cell in the plan grid reach the generation?

**Decision:** **`GenerateLocalesCommand` takes a set of skipped (file, locale) pairs.** A whole row or column still
goes through what exists, `include`/`exclude` and `targets`; a single cell goes into `skip`. The handler leaves those
jobs out before the engine starts, and the receipt does not list them.

- **Why:** the grid needs single cells ("fine in `de`, redo it in `fr`"); the change is small and testable in the
  handler alone.
- **Not chosen:** rows and columns only (no single cells, which the issue asks for); a CLI `--skip file:locale` in
  this story (only the TUI needs single cells today).
- **Consequence:** a TUI run with single cells off has no exact CLI equivalent. A `--skip` flag can be a follow-up.
