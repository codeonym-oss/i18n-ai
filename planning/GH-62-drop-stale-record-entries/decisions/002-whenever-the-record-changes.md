# 002: The record is rewritten whenever its content changes

**Date:** 2026-11-09 (grilling, Q2; agreed: "ok", to the recommended option 1)

**Question:** when does `generate` drop the entries of decision 001?

**Found:** the handler rewrites the record only when the run wrote a target (`if written:`, the `finally` block of
`GenerateLocalesCommandHandler.handle`).

**Decision:** **on every run that reaches the engine, the record is rewritten when its content differs from what
was read**, even if the run wrote nothing (every target failed, or it was interrupted), and removed when it ends up
empty (GH-15 decision 009). A run that changes nothing leaves the file untouched. `--dry-run` stops before the
engine and never touches it.

- **Why:** the drop does not depend on what the run wrote, so tying it to a write would leave it to chance;
  comparing first keeps diffs free of noise.
- **Not chosen:** only when a target is written, as today (a run that writes nothing leaves the stale entries until
  a later one writes).
