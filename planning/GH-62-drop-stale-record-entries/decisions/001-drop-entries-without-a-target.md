# 001: `generate` drops the entries whose target the tree no longer has

**Date:** 2026-11-09 (grilling, Q1; agreed: "ok", to the recommended option 1)

**Question:** which stale entries of `.i18n-ai-fallbacks.json` does `generate` drop?

**Found:** every target a run translates is written (`settle`), and its entries are replaced (GH-29 decision 002),
so a deleted message leaves the record as soon as its target is written again. The entries that stay for good are
those of targets no run writes: (1) a source file removed or no longer qualifying, (2) a locale removed from disk,
(3) a deleted message in a target this run left out, (4) a locale on disk but not in this run.
`ListFallbacksQueryHandler` already tells (1) and (2) apart: it maps every qualifying source file × every locale on
disk (`--include` and `--exclude` cleared) to its place in the record, and an entry matching none has no target.

**Decision:** **`generate` drops the entries that match no target of the tree, cases 1 and 2, by the same mapping
as the review**; cases 3 and 4 are kept. This changes GH-29 decision 002's "leaves the others" for those entries
only.

- **Why:** an entry with no target describes nothing on disk, so dropping it loses nothing; the review and
  `generate` agree on what has no target.
- **Not chosen:** also case 3 (every untouched target's source schema read on every run, for entries the next write
  of that target clears anyway); only case 1 (a removed locale's entries would stay for good, though they point at
  nothing).
