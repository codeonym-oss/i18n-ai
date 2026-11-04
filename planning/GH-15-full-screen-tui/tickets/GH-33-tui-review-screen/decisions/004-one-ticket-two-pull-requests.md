# 004: One ticket, two pull requests: the intents, then the screen

**Date:** 2026-11-04 (ticket pass, Q4; agreed: "1, go with your recommendation")

**Question:** with three commands, a query and a screen (decisions 001–003), does the ticket split (story decision
010 allows it)?

**Decision:** **one ticket, shipped as two pull requests.** The first holds the domain and application changes:
`LocaleDocument.with_value`, `MessageUnknown`, `ListFallbacksQuery`, `SetMessageCommand`, `RetryFallbacksCommand`,
`AcceptFallbacksCommand`, their wiring and handler tests; its body says `Part of #33`. The second holds the review
screen, its ways in, the `Pilot` tests and the story-level run; it says `Closes #33`.

- **Why:** each pull request stays reviewable (about 500 lines each), and the intents still land in the ticket of
  their first user.
- **Not chosen:** two tickets (a new issue and a second ticket pass, for the same plan); one pull request (about
  1000 lines).
- **Cost accepted:** the first pull request merges intents nothing calls yet, for the days until the second.
