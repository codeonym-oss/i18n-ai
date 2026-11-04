# 007: A stale record entry is shown, and can only be accepted

**Date:** 2026-11-04 (ticket pass, Q7; agreed: "1, go with your recommendation")

**Question:** what does the review do with a record entry whose message, source file or locale is gone?

**Found:** `generate` rewrites a target's entries only when it writes that target
(`GenerateLocalesCommandHandler.handle`, the `finally` block), so such an entry stays in the record for good.

**Decision:** **`ListFallbacksQuery` returns it with no source text; the screen says "no longer in the source" and
offers only accept,** which takes it out of the record. Set-message refuses it (`MessageUnknown`, decision 003),
and retry leaves it out.

- **Why:** nothing disappears unseen, and one key clears it; the CLI's behaviour is unchanged (story rule).
- **Not chosen:** leaving stale entries out of the list (they stay in the committed record, unseen); `generate`
  dropping them (changes the CLI; a follow-up if wanted).
