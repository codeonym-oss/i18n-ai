# 005: Home shows the tree the setup would pick

**Date:** 2026-11-10 (grilling, Q5; agreed: "ok", to the recommended options 1 and 4)

**Question:** which tree does Home describe when the TUI opens?

**Found:** no new query is needed: `ScanLocaleTreeQuery` gives `reusable` and `to_translate` per target × file
(coverage is reusable ÷ (reusable + to_translate)), and `ListFallbacksQuery` the banner.

**Decision:** **the tree the setup would pick by default:** the saved answers' tree, else the first one
`DetectLocaleTreesQuery` finds. Home shows its existing locales against its source files. With several trees found,
the command bar offers a tree switcher, and a new run's setup starts on the tree Home shows. With none found, Home
shows an empty state pointing to New run, where a path can be typed.

- **Why:** Home and the setup always mean the same tree; one scan when the TUI opens.
- **Not chosen:** every detected tree at once (a scan per tree on each open, cramped at 80 columns); an empty Home
  until a run is set up (no dashboard).
