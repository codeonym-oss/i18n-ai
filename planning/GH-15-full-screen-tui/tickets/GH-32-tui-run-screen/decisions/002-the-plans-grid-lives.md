# 002: The run screen is the plan's grid, its cells live

**Date:** 2026-10-29 (ticket pass, Q2; agreed: "ok", to the recommended option 1)

**Question:** how is the run screen laid out?

**Decision:** **the plan screen's files × locales grid, each cell showing its job's state as it changes:** waiting,
translating, retry k/n, written, partial, failed, ignored, or off (turned off in the plan). Under it, a progress bar,
then **Problems**: the failures and partial files as they arrive. When the run ends, the receipt and "To run it
again" replace the grid, as GH-30's decision 004 has them.

```
┌ i18n-ai ─ run ──────────────────────────────────┐
│ File              fr            de              │
│ auth/login.json   ✓ written     ⟳ retry 2/3     │
│ common.json       … translating off             │
│ ▓▓▓▓▓▓▓▓▓▓░░░░░░░░  2/3                          │
│ Problems                                        │
│  common.json → it: 1 message kept its source    │
└ b back (once done)  q quit ─────────────────────┘
```

- **Why:** the grid the person just planned, filling in; the problems stand out in a large run.
- **Not chosen:** a row per job (long, and unlike the plan); the log with a line of the jobs in flight (the retries
  gone once a job is done).
- **Consequence:** the plan and the run screens share the grid's code.
