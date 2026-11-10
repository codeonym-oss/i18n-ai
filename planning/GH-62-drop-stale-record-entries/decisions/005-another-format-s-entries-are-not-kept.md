# 005: another format's entries, in a tree that mixes formats, are not kept apart

**Date:** 2026-11-10 (ticket pass, Q2; agreed: "ok", to the recommended option)

**Question:** in a tree that mixes formats, read in one of them (the preset's, or `-f`), what happens to the record's
entries of the other format's targets?

**Found:** the scanner reads one format of a mixed tree, and refuses it otherwise (`MixedLocaleFormats`); the record
is one per directory. The other format's targets are not in the mapping, so their entries have no target, as the
review already shows them.

**Decision:** **they are dropped like any entry with no target**, and the draft says so under "Out of scope".

- **Why:** it takes a mixed tree and runs with different `-f`; keeping them would need each format's extensions in
  the application layer, which only infra knows today.
- **Not chosen:** keeping the entries whose target's suffix is not the scanned format's.
