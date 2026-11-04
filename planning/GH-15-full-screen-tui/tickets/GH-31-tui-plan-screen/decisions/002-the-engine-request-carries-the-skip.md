# 002: The engine request carries the skip set

**Date:** 2026-10-29 (ticket pass, Q2; agreed: "ok", to the recommended option 1)

**Question:** the engine pairs each file with each target itself (`graph.py:dispatch_jobs`); where does a skipped
(file, locale) pair stop?

**Decision:** **`GenerateLocalesCommand.skip` goes on to `EngineRequest.skip`, and `dispatch_jobs` sends no job for
a skipped pair.** The handler also leaves out a file whose every target is skipped (it is not even classified), reads
no existing target for a skipped pair, and starts the progress with the jobs that remain. Skipped pairs are not in
the receipt (story decision 005).

- **Why:** a cell turned off costs no model call; one field on the port and one filter in the graph.
- **Not chosen:** the handler discarding the skipped pairs' results (the model is still called and paid); one
  engine run per locale (classifies every file again, and `concurrency` no longer holds across locales).
