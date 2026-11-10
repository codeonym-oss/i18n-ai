# Drop the fallback record's entries whose target is gone

## Problem

`generate` rewrites a target's entries in `.i18n-ai-fallbacks.json` only when it writes that target. An entry whose
source file was removed (or no longer qualifies), or whose locale was removed from disk, describes a target that no
longer exists, yet it stays in the committed record for good. The TUI's review shows such an entry as "no longer in
the source" and lets you accept it (GH-33 decision 007), but nothing else ever clears it.

Takes up the follow-up `planning/GH-15-full-screen-tui/follow-ups/2026-11-04_1058_generate-drops-stale-record-entries.md`.

## Fix

- `generate` drops every record entry that matches no target of the tree: no qualifying source file, or no locale
  on disk, for it. It uses the same mapping as the review's `ListFallbacksQuery`, so the two agree on what has no
  target (decision 001).
- This happens on every run that reaches the translation, even one that writes nothing. The record is rewritten
  only when its content changes, and removed when it ends up empty (decision 002).
- `-v` shows a log line naming how many entries were dropped and their target files; the receipt is unchanged
  (decision 003).

## Out of scope

- Entries of a message deleted from the source, in a target this run did not write: the next write of that target
  clears them, as today.
- Entries of a locale still on disk but not generated in this run: it may only be left out this time.
- Entries of another format's targets, in a tree that mixes formats and is read in one: they have no target, and
  are dropped (decision 005).
- The TUI's retry and accept, and the `scan` precheck.

## Done when

- After a source file is removed, a `generate` run leaves none of its entries in the record, and the record is
  removed when nothing else is in it.
- After a locale's directory is removed, its entries leave the record on the next run.
- A run that writes nothing (every target failed) still drops them.
- Entries of a locale not in the run, and of files excluded with `--exclude`, stay.
- A run with nothing to drop and nothing to record leaves the record file untouched.
- `-v` shows the "dropped N fallback record entries with no target" line.
