# 004: A `:name` keeps its name; its case may change

**Date:** 2026-10-23 (grilling, Q4; agreed: "ok", to the recommended option 1)

**Question:** must a translation keep the case of a Laravel placeholder (`:name`, `:Name`, `:NAME`)?

**Decision:** **the name is compared without its case.** `:name` → `:Name` passes; a lost, added or renamed
placeholder (`:name` → `:nom`) is rejected, each as often as it appears. The model is told what each case renders
(as is, capitalized, in capitals), to change it only where the grammar wants it.

- **Why:** Laravel fills all three from the same variable; the case is presentation. A placeholder moved to the start
  of a German or French sentence rightly becomes `:Name`.
- **Not chosen:** an exact match (correct translations rejected and retried); a warning on a case change (a new kind
  of outcome for one case).
