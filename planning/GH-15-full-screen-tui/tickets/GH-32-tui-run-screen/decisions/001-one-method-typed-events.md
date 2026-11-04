# 001: The progress port takes one typed event at a time

**Date:** 2026-10-29 (ticket pass, Q1; agreed: "ok", to the recommended option 1)

**Found:** with `astream(..., stream_mode=["updates", "custom"], subgraphs=True)`, events the atom writes with
LangGraph's `get_stream_writer()` reach the engine's stream live, from inside the nested `atom.ainvoke` (checked on
langgraph 1.2.16); the atom can tell its start and each retry without changing the engine port's shape.

**Question:** what shape does `IGenerationProgress` take for story decision 004's typed events?

**Decision:** **one method, `on(event)`, over a union of small dataclasses:** `RunStarted(jobs)`,
`JobStarted(file, target)`, `JobRetrying(file, target, messages, attempt, attempts)`, `JobDone(result: FileResult)`,
`FileDropped(file, jobs, reason)`, `RunFinished()`. An adapter matches on the type; the TUI posts each event to its
screen as one Textual message; the console adapter renders what it renders today and lets the rest fall through.

- **Why:** what decision 004 describes, and the shape the engine's own events already have (`EngineEvent`, matched in
  the handler).
- **Not chosen:** a method per event (each new event a method on every adapter, empty ones on the console's, and a
  Textual message class per method).
