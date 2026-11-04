# Record the fallbacks, and translate them again

## Problem

A message that keeps failing the rules is written in its source text, the fallback, so its file stays whole. That
text breaks no rule (it only warns `unchanged`), so the next run keeps it as a good translation: without
`--overwrite`, a fallback is kept for good, and nothing on disk tells it from a message that is rightly the same in
both languages ("Dashboard").

## The change

- A generation records each fallback it writes, per target file: the key path, the rule it broke and the model's
  last rejected translation, in `.i18n-ai-fallbacks.json`, in the directory the targets are written to (story
  decisions 008, 009). The record is committed with the locales.
- The next run translates a recorded fallback again instead of keeping it; when it passes, it leaves the record.
  The record is removed when empty.
- The scanner never reads the record as a locale.
- The record holds each fallback's last rejected translation, which the review screen (ticket 5) shows; the
  receipt is unchanged (decision 003).

## Out of scope

- Any TUI work; the review's edit, retry and accept (ticket 5).

## Done when

- [ ] A CLI run with a message that keeps failing writes its fallback and records it; the next run sends that
      message to the model again, and a passing translation leaves the record.
- [ ] A file-per-locale tree with the record beside `en.json` scans as before.
- [ ] A run with no fallbacks writes no record.

Settled in the ticket pass: the handler leaves recorded fallbacks out of the existing targets it gives the engine
(decision 001); the record is a flat, sorted, versioned list (decision 002).
