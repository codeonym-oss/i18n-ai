# 003: Set-message sets any message of a target

**Date:** 2026-11-04 (ticket pass, Q3; agreed: "1, go with your recommendation")

**Question:** does set-message take any message of a target, or only a recorded fallback?

**Decision:** **any message.** `SetMessageCommand(tree, target, file, path, text)`: the schema is built from the
source file, the unit at the target path found, the text normalized and checked; with no error it is written at
that path of the target document (a new `LocaleDocument.with_value`) through `ILocaleStore.write`, and when the path
is recorded it leaves the record. A text that breaks a rule is refused with its violations, and nothing changes. A
path that is no message of the source's schema is refused (`MessageUnknown`).

- **Why:** the general intent a later `i18n-ai review` uses (story decision 002), at no extra cost.
- **Not chosen:** recorded fallbacks only (one more check and error, which the later command would lift).
