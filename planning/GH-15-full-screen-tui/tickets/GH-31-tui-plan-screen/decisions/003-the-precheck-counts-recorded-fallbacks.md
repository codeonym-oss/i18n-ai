# 003: The precheck counts the recorded fallbacks as to translate

**Date:** 2026-10-29 (ticket pass, Q3; agreed: "ok", to the recommended option 1)

**Found:** `ScanLocaleTreeQueryHandler` never reads `.i18n-ai-fallbacks.json` (story decision 009), so a message
that fell back counts as reusable, while the run translates it again. The CLI's precheck has the same gap since
GH-29.

**Decision:** **fixed in this ticket.** The scan reads the record and takes the recorded paths out of each existing
target before counting what is reusable, as `GenerateLocalesCommandHandler` does (`document.without(paths)`). An
integration test proves a recorded fallback counts as to translate.

- **Why:** the grid's numbers are its point; the fix repeats a step the generate handler already has.
- **Not chosen:** a follow-up (wrong counts until it is done); a separate "retried" count per cell (a view field and
  more text in every cell, for what the review screen, GH-33, shows).
