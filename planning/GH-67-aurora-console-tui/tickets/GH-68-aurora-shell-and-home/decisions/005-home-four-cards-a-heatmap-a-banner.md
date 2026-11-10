# 005: Home has four cards, a heatmap and the fallback banner

**Date:** 2026-11-10 (ticket pass, Q5; agreed: "ok", to the recommended option 1)

**Question:** what does Home show without run history (story decision 001)?

**Decision:** **from the scan and the fallback record alone:**

- **Four KPI cards:** COVERAGE, the share of the targets' messages already translated; MESSAGES, the source's
  messages and in how many files; FALLBACKS, the recorded count, amber when any; LOCALES, the targets' count and
  codes, with the source (in place of v2's "last run").
- **The heatmap:** a row per locale, a column per file; each cell its coverage % on v2's five-step mint scale, with
  "◐ n" when it holds fallbacks; each row its total ("74/75").
- **The banner:** "n fallbacks kept their source text · Review v", leading to the Review mode.
- No deltas, sparklines, messages/files toggle or recent runs; the heatmap takes the recent runs' width.

- **Why:** v2's dashboard, with every number one the tree gives today.
- **Not chosen:** the messages/files toggle (a second view the cells already tell); the heatmap and banner alone
  (no dashboard).
