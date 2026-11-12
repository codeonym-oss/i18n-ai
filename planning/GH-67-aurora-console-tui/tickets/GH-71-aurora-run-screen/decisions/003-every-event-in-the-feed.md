# 003: Every event in the feed, a pop-up for each problem and the end

**Superseded by 006** on what the feed and the receipt say of each job.

**Date:** 2026-11-12 (ticket pass, Q3; agreed: "ok", to the recommended option 1)

**Question:** what goes in the events feed, and what pops up?

**Decision:** **every event in the feed, newest on top; a pop-up for a partial job, a failed job, a dropped file
and the end of the run.** The feed replaces the "Problems" log. A line is the time so far, a glyph, the job and a
detail:

- `◆ run started · 11 jobs · 201 messages`;
- `▸ translating`;
- `⟳ 3 messages sent back · attempt 2/3`;
- `● written · 12 translated, 26 kept`;
- `◐ partial · app.welcome fell back` (up to 3 keys from the result's failures, then `+N`);
- `✕ failed · <reason>`;
- `ignored · <reason>`, for a dropped file;
- `◆ run finished`.

v2's `all | problems` switch is on `p`: problems keeps the retry, partial, failed and ignored lines. The pop-ups are
Textual notifications.

- **Why:** the feed is the whole story, `p` narrows it to what needs a look; the pop-ups are what is missed while
  looking at the grid ("a retry or a dropped file is easy to miss").
- **Not chosen:** no "translating" lines (the feed no longer says when a job began); pop-ups only for a dropped file
  and the end (a partial or failed job seen only in the feed and the grid).
- **Found:** a retry names how many messages go back, not which keys; a done job's failures do name its keys.
