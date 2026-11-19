# 001: The editor is part of the review screen

**Date:** 2026-11-19 (ticket pass, Q1; taken as recommended after the person asked to "finish all the remaining tasks", no answer given to the question itself)

**Question:** does the fix stay a modal dialog (`EditScreen`), or does the editor sit in the screen beside what it
fixes?

**Decision:** **the editor is in the screen.** The list of fallbacks on the left (on top when narrow, story decision
002); beside it, for the fallback under the cursor, a header (locale · file · key, the rule, `1 of 5 · 2 marked`),
three cards (SOURCE, MODEL · last attempt, IN THE FILE NOW), the editor with its check line, and the keys.
`e` or `tab` moves into the editor; `enter` there saves and moves on to the next fallback; `escape` leaves it, so
space, `r` and `a` act on the list again. `EditScreen` goes.

- **Why:** the draft's problem is that the source, the rejected text and the fix are never side by side.
- **Not chosen:** the restyled dialog (the comparison hidden while typing); both, the dialog when narrow (two ways to
  test for one action).
- **Left out:** v2's `⌃I` (insert a placeholder) and `⌃M` (take the model's text): `⌃M` is `enter` in a terminal,
  and neither is in the draft.
