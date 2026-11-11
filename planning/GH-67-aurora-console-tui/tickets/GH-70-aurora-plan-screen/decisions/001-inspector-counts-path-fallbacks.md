# 001: The inspector shows the cell's counts, its path and its recorded fallbacks

**Date:** 2026-11-11 (ticket pass, Q1; agreed: "ok", to the recommended option 1)

**Question:** what does the inspector show, when the scan gives a cell's counts but no list of its messages?

**Decision:** **what the queries already give, with no tabs.** For the cell under the cursor: its state (new, fill,
up to date, off) and its counts (to translate, kept), the target file's path, and the cell's recorded fallbacks, each
with its key and source text and a FALLBACK tag. The fallbacks come from `ListFallbacksQuery`, sent once when the
plan opens.

- **Why:** everything known about the cell, nothing that suggests more; the draft's "its counts, its fallbacks, its
  path"; no new query (the story's rule).
- **Not chosen:** v2's Messages / Kept / File tabs (mostly empty, suggesting a list that is not there); v2's full
  message list with MISSING and BROKEN reasons (a new per-message query, against the story's rule).
