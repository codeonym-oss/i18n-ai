# 009: The fallback record sits with the locales it describes

**Date:** 2026-10-26 (grilling, Q9; agreed: "ok", to the recommended option 1)

**Question:** where does the fallback record (decision 008) live?

**Decision:** **one record per tree, `.i18n-ai-fallbacks.json`, in the directory the targets are written to** (the
tree's directory, or `--output`), committed with the locales. Its paths are relative to that directory. It is
written only when a run leaves or clears a fallback, and removed when it is empty.

- **Why:** it describes the locale files, so it travels with them: a teammate's clone and a CI `generate` see the
  same fallbacks and translate them again.
- **Not chosen:** i18n-ai's state directory, as the answers are (the record would exist on one machine only, and a
  CI run would keep the fallbacks silently); one `.i18n-ai/fallbacks.json` at the project root for every tree
  (paths across trees and outputs; one tree's run rewrites another's record).
- **For the ticket pass:** the scanner must never read the record as a locale (in a file-per-locale tree it sits
  among `en.json`, `fr.json`).
