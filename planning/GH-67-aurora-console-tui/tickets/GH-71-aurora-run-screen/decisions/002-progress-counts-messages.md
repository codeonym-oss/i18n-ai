# 002: The progress card counts messages, and the time so far

**Date:** 2026-11-12 (ticket pass, Q2; agreed: "ok", to the recommended option 1)

**Question:** what does the progress card count?

**Decision:** **messages.** Each job counts its planned messages (the plan's "to translate" for its cell) when it
ends. The card shows:

- **DONE**, the percentage of the planned messages whose job has ended;
- **a bar** in proportion by message: mint written, amber partial, coral failed, the rest still to come;
- `7/11 jobs · 129/201 messages · ⟳ 3 ◐ 1 ✕ 0`: retries, partial jobs, failed jobs;
- **the time so far** (`00:42`), in the card and the status line.

A dropped file's jobs leave both totals. The time left and the messages per second stay out (story decision 001).

- **Why:** a 400-message file and a 3-message one do not weigh the same; messages are what the plan's run bar
  counted (GH-70 decision 004). The clock shows a long run is alive between events.
- **Not chosen:** a percentage of jobs (a big file left last holds the bar at 90%); no clock (nothing moves between
  events).
