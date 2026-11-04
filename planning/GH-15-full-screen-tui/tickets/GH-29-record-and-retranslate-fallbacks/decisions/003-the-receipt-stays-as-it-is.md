# 003: The rejected text goes to the record; the receipt stays as it is

**Date:** 2026-10-26 (ticket pass, Q3; agreed: "ok", to the recommended option 1)

**Question:** does `FileResult` in the receipt carry the rejected translation too?

**Decision:** **no.** The atom puts each fallback's last rejected text on `FileTranslated`, the handler writes it to
the record, and the receipt is unchanged. The review reads the record (story decision 008). The draft's "the receipt
carries the rejected translation" is corrected.

- **Why:** one place holds the fallbacks; the review needs the record anyway, for earlier runs.
- **Not chosen:** a copy on `FileResult` (two copies of one thing, for a receipt screen that can read the record).
