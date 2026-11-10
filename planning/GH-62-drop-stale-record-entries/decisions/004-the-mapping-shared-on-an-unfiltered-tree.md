# 004: the mapping is shared, and built on a tree without `--include` and `--exclude`

**Date:** 2026-11-10 (ticket pass, Q1; agreed: "ok", to the recommended option)

**Question:** how does `generate` know every target of the tree, when it scans with `--include` and `--exclude`
applied?

**Found:** `generate` scans `command.tree` as given, so an excluded file is not in `tree.files`: a mapping built from
that tree would drop its entries, against decision 001. `ListFallbacksQueryHandler` scans with both cleared, and
builds the mapping in its step 1.

**Decision:** **the mapping moves to `application/common/fallbacks.py` as `record_targets(tree)`**, every qualifying
source file × every locale on disk but the source, by its place in the record, used by the review and by
`generate`. **`generate` scans again with `include=()` and `exclude=()` only when the command has either**;
otherwise it maps its own tree.

- **Why:** one mapping, so the two agree (decision 001); the second scan reads files but sends nothing to a model,
  and only filtered runs pay for it.
- **Not chosen:** finding an entry's source file from its target file: it depends on each layout, and repeats
  `target_location` backwards.
