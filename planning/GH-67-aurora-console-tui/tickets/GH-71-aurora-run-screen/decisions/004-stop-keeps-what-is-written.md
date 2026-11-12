# 004: ⌃C stops the run; what is written stays

**Date:** 2026-11-12 (ticket pass, Q4; agreed: "ok", to the recommended option 1)

**Question:** does this ticket add v2's Stop (⌃C, "what is written stays")?

**Found:** each target is written atomically (`write_atomically`), and the handler writes the fallback record in a
`finally`, so a cancelled run keeps every finished job and records its fallbacks. Textual binds `ctrl+c` to
`help_quit`; a screen's binding takes it over.

**Decision:** **yes, with no confirmation.** `ctrl+c` on the run screen, while it runs, cancels the run's worker.
The jobs done stay written; the cells of the others read "stopped"; the feed and a pop-up say
`■ stopped · 7 of 11 jobs done`. There is no receipt (the command never returned); the screen shows the command
that runs it again, and Back. Nothing new underneath: no command, no query.

- **Why:** today a run stops only by quitting the app; the write and the record already hold under a cancel.
- **Not chosen:** a follow-up (v2's Stop with nothing behind it); a confirmation first (a screen more, and a stop
  loses nothing: the next run does the rest).
