# 005: One ticket, one pull request

**Date:** 2026-10-23 (grilling, Q5; agreed: "2")

**Question:** should the Laravel work (preset, detection on every run, keys as the source, `:name`, pipe plurals) be
one ticket, or split in two (JSON trees with `:name`, then pipe plurals)?

**Decision:** **one ticket, shipped in one pull request.** The pipe plurals are part of it, so no interim behaviour
for pipe messages is needed.

- **Why:** the person's choice: less overhead for one library's support.
- **Not chosen:** two sub-issues under #17, A then B (smaller reviews, an interim "pipe messages kept as source");
  B first (plurals without a tree to use them).
- **Cost accepted:** a larger diff spanning the scanner, the rules and the plural logic; the commits inside the pull
  request should keep those apart for review.
