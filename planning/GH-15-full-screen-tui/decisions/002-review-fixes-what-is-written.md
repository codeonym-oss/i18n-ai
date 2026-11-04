# 002: The run writes as it goes; the review fixes what is written

**Date:** 2026-10-26 (grilling, Q2; agreed: "1")

**Question:** does the review happen before the files are written, or after?

**Decision:** **after.** The generation writes each file as soon as it is translated, as the CLI does today, with a
message that kept failing in its source text (the fallback). The review screen lists those messages, each with its
source, the model's last rejected translation and the violated rule, and offers:

- **edit:** the text is checked against the rules and, when it passes, written into the target file at once;
- **retry:** the model translates those messages again, and what passes is written;
- **accept:** the fallback stays.

Two new application intents carry this (set a message, retry messages), usable later outside the TUI (an
`i18n-ai review`, not part of this story). The receipt carries what the review needs, the rejected translation
included. The issue's "then write" becomes "each fix is written as it is made".

- **Why:** one generation model for the CLI and the TUI; a crash or a closed terminal never loses translated work
  (the handler writes as it goes for that reason).
- **Not chosen:** holding every write until the review (loses a run on a crash, and the TUI would generate
  differently from the CLI); writing only clean files and holding the others (two write paths, still loses the held
  files).
