# 006: A job's reasons, warnings and path go in the feed

**Date:** 2026-11-12 (ticket pass, Q6, from a side agent's note; agreed: "ok", to the recommended option 1)

**Supersedes 003 and 005** on what the feed and the receipt say of each job; the rest of both stands.

**Question:** with Rich's receipt gone from the TUI (decision 005), where do a job's fallback reasons, its warnings
and its written path go?

**Found:** `render_receipt` lists, under its table, each job's failures with their reason (`violation.message`) and
its warnings, eight per job (`_LISTED`) then "… and N more"; the table holds each written path. Decision 003's feed
named up to three fallen-back keys, without their reason; warnings and paths were shown nowhere.

**Decision:** **in the feed, under the job's line.**

- A partial, refused or failed job's line is followed by a sub-line per fallen-back key with its reason
  (`app.welcome · missing {{name}}`), eight per job, then `… and N more`; its line says `◐ partial · 1 fallback`.
- A job with warnings adds `! 2 warnings` and a sub-line per warning, the same way.
- A written job's line ends on its path, as the CLI shows it (`● written · 12 translated, 26 kept ·
  locales/de/common.json`).
- The `p` switch keeps the reasons and the warnings.

- **Why:** all that Rich's receipt said is back, in one place, in the order of the jobs.
- **Not chosen:** a "Notes" card under "Run it again" (the reasons only once the run ends, and the paths still
  without a place); leaving it (warnings and paths lost from the TUI).
