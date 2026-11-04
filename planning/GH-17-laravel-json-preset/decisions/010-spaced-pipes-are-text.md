# 010: A pipe with spaces around it, and no range, is text

**Date:** 2026-10-23 (ticket pass, Q4; agreed: "ok", to the recommended option 1)

**Supersedes 002** in part: which messages are pipe plurals.

**Question:** Laravel splits pipes only in `trans_choice`; a key used with `__()` (`"Dashboard | Acme"`) is shown as
it is. Which messages are pipe plurals?

**Decision:** **a message with a range (`{0}`, `[1,19]`, `[20,*]`) or an unspaced `|` is a pipe plural; one whose
every pipe has a space on both sides, and no range, is text.**

- **Why:** Laravel trims ranged forms but not unranged ones, so real plurals are written unspaced (`apple|apples`,
  as Laravel's docs write them); titles and breadcrumbs are written ` | `.
- **Not chosen:** every pipe a plural (titles split into forms); requiring `:count` or a range (misses
  `apple|apples`).
- **Cost accepted:** a plural written `one apple | many apples` is translated as one text, its pipes kept.
