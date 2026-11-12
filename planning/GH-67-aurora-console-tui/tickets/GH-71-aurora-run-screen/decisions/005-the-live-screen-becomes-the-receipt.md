# 005: The live screen becomes the receipt

**Superseded by 006** on what the feed and the receipt say of each job.

**Date:** 2026-11-12 (ticket pass, Q5; agreed: "ok", to the recommended option 1)

**Question:** what does the end of the run look like?

**Decision:** **the run screen stays, and turns into the receipt.**

- The progress card becomes four `KpiTile`s: FILES WRITTEN, TRANSLATED, FALLBACKS, FAILED.
- The grid stays, each card in its final state with its counts.
- The feed stays, and ends on `◆ run finished · Generated with <model>`.
- A "Run it again" card takes the bar's place: the command, the note on single cells off, `y` copies the command
  (Textual's `copy_to_clipboard`), and `v` Review when the run left fallbacks.
- Rich's receipt table goes from the TUI (the CLI keeps it): the grid holds each job's status, translated and kept,
  the feed its reason and fallen-back keys. The receipt board's "by locale" card is left out; the column heads carry
  each locale's count.

- **Why:** nothing jumps or vanishes at the end; the grid one watched is the receipt.
- **Not chosen:** the tiles plus Rich's table below the grid (each job twice); a Receipt screen pushed at the end
  (a screen more, Back and the Run section's return land on it).
