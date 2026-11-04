# 014: The keys' source: its order, how the scan shows it, the targets' style

**Date:** 2026-10-23 (ticket pass, Q8; agreed: "ok", to the recommended option 1)

**Question:** with no `lang/en.json`, in what order are the source's keys, what does the scan show as the source,
and how are new targets written (indent, newline), with no source file to copy?

**Decision:** **the keys in order of first appearance, the locale files read in name order; the scan shows the
source as `en (the keys of de.json, fr.json)`; a new target is written in the first locale file's style.** The tree
says where its source came from (a `source_from` field) for the scan to show it.

- **Why:** the authors' grouping of their keys is kept; the scan names only files that exist.
- **Not chosen:** a made-up `lang/en.json` shown as the source path (a file that is not there); keys sorted
  alphabetically (the grouping lost).
