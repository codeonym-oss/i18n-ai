# 004: Progress flows as typed events, from the atom to the screen

**Date:** 2026-10-26 (grilling, Q4; agreed: "ok", to the recommended option 1)

**Question:** how does the run screen see each file × locale live, retries included?

**Decision:** **typed progress events end to end.** The engine yields two new events, an atom started and an
attempt rejected (how many messages, which attempt of how many). The handler passes every event to the progress
port, which takes typed events instead of a description string: started, retrying, done (with its `FileResult`),
dropped. The console adapter renders what it renders today and ignores the rest; the TUI renders all of them.

- **Why:** the only way the TUI stays on the mediator (#15: "the same queries and commands as the CLI") and still
  shows retries as they happen.
- **Not chosen:** the TUI driving `ITranslationEngine.run` itself (duplicates the handler's qualifying and writing,
  bypasses the mediator); only a richer "done" (no retries live, half of the run screen).
- **Touches:** the engine port, the langgraph atom, `GenerateLocalesCommandHandler`, `IGenerationProgress`, the
  console adapter. The CLI's output does not change.
