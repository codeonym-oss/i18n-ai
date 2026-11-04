# 001: The keys are the source text, en.json first

**Date:** 2026-10-23 (grilling, Q1; agreed: "ok, so its 2")

**Question:** where does a Laravel JSON tree's source text come from, when most projects have no `lang/en.json`?

**Decision:** **`lang/en.json` when it exists; otherwise the keys of the existing locale files, all together, are
the English source**, each key's text being the key itself, as gettext's `msgid` is.

- **Why:** Laravel's JSON keys are the English strings, and most projects only ship the target files
  (`lang/fr.json`), the English living in the PHP code. Requiring `en.json` would leave most real projects out.
- **Not chosen:** requiring `lang/en.json` (the preset would fit few projects as they are); extracting the strings
  from the PHP code (`__()`, `trans()`, `@lang`), a PHP scanner of its own, left for a later ticket. Strings found
  only in code are therefore not translated by this ticket.
