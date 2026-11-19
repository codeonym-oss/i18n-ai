# 005: The review's scan keeps the format read (follow-up taken up)

**Date:** 2026-11-19 (ticket pass, Q5; taken as recommended after the person asked to "finish all the remaining tasks", no answer given to the question itself)

**Question:** decision 004 changes `ListFallbacksQueryHandler`; take up the follow-up
`review-scan-loses-the-format` there?

**Decision:** **yes.** The handler scans the tree as asked, then, when it has `include` or `exclude`, the whole tree
in the format read (`format=tree.format`), as `generate` does since GH-62. Tested on a mixed tree whose YAML files
are excluded.

- **Why:** the same file is open, and the fix is the one `generate` has.
