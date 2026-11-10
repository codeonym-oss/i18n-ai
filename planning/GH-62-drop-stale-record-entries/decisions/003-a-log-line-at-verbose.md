# 003: The drop is told by a log line at `-v`, not in the receipt

**Date:** 2026-11-09 (grilling, Q3; agreed: "ok", to the recommended option 1)

**Question:** does `generate` say it dropped record entries?

**Decision:** **an info log line, shown at `-v`**, naming how many entries were dropped and their target files, e.g.
"dropped 2 fallback record entries with no target: fr/old.json, de/old.json". The receipt is unchanged
(GH-29 decision 003).

- **Why:** what is dropped pointed at nothing, so it is no result of the run; the record is committed, so its diff
  shows the change too.
- **Not chosen:** a line under the receipt (changes its shape for a cleanup that loses nothing); nothing at all (no
  trace for someone wondering why the record shrank).
