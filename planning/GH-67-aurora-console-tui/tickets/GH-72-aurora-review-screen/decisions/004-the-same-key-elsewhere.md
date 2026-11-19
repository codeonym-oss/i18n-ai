# 004: The same key elsewhere: the tree's other targets, through the review's own query

**Date:** 2026-11-19 (ticket pass, Q4; taken as recommended after the person asked to "finish all the remaining tasks", no answer given to the question itself)

**Question:** how far can "the other locales of the same key" go on the tree alone (story decision 001)?

**Decision:** **the same message in every other target locale the tree has, as its file holds it now.**
`FallbackView` gains `elsewhere`: for each other existing target locale of the same source file, its code and the
message's current text there (None when the file or the message is missing). `ListFallbacksQuery` fills it from the
targets it already finds; the panel THE SAME KEY ELSEWHERE lists them, `—` for a missing one. A stale entry has
none.

- **Why:** the tree holds the targets' files; the query already reads them for `current`. A field on an existing
  view is no new query (story rule).
- **Not chosen:** only the same key's other recorded fallbacks (often none); dropping the panel.
