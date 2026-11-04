# 001: Retry goes through `EngineRequest` as it is, from a handler of its own

**Date:** 2026-11-04 (ticket pass, Q1; agreed: "1, go with your recommendation")

**Question:** retry needs the engine to translate only some messages of a file: through `EngineRequest`, or a
request of its own?

**Found:** since #29 (its decision 001) the generate handler leaves recorded fallbacks out of the existing targets
it gives the engine, and the atom translates every unit `reusable_translations` does not keep. A fallback holds its
source text, which breaks no rule (`unchanged` is a warning), so it is reusable while it stays in `existing`.

**Decision:** **a `RetryFallbacksCommand` with a handler of its own, sending an unchanged `EngineRequest`.** It holds
only the file × locale jobs the chosen fallbacks are in; each job's `existing` is the target without the chosen
paths only, so the engine translates those and reuses the rest, the other fallbacks included. The handler writes
each translated file and updates the record itself: the chosen entries leave it, and those that fail again come
back with their new rejected translation and problems.

- **Why:** no change to the engine port, the run graph or the atom; the seam that exists already selects what is
  translated.
- **Not chosen:** an `only: paths` field on `EngineRequest` (touches the port, the graph and the atom for one
  edge case); `GenerateLocalesCommand` cut to the cell (retries every fallback of the cell, not the chosen ones,
  rewrites the cell's whole record, and classifies again).
- **Accepted edge:** a message the target lacks that was never recorded (the source gained a key since the last
  run) is translated too; the next `generate` would translate it anyway.
