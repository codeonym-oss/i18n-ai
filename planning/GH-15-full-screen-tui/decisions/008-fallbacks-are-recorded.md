# 008: The fallbacks are recorded, and the next run translates them again

**Date:** 2026-10-26 (grilling, Q8; agreed: "ok", to the recommended option 1)

**Question:** where does the review's list come from, and does it outlive the run?

**Found:** a fallback is the source text, which breaks no rule but warns `unchanged`; `reusable_translations`
(`domain/sub_domains/locale/rules/translation.py`) keeps every message without errors, so the next run keeps a
fallback for good (without `--overwrite`), in the CLI today. Nothing on disk tells a fallback from a message that
is rightly the same in both languages ("Dashboard").

**Decision:** **the generation records its fallbacks**, per target file: each message's key path, the rule it broke
and the model's last rejected translation.

- The next run, CLI or TUI, translates a recorded fallback again instead of keeping it; one that passes leaves the
  record.
- The review screen reads the record, so it shows the current run's fallbacks and those earlier runs left, the
  CLI's included. Edit, retry and accept update it (accept: the message stays as it is and leaves the record, so it
  is kept from then on).
- Where the record lives is decision 009.

- **Why:** decision 002 has the review fix what is on disk; a record makes that hold across sessions, and closes
  the CLI's silent keeping of fallbacks with the same change.
- **Not chosen:** the current run's receipt only (a fallback not fixed before the TUI closes is kept for good);
  a marker inside the target files (JSON has no comments; a marker in the value ships to users).
