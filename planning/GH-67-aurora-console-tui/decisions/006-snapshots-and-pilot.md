# 006: Pilot tests the behaviour, SVG snapshots the look

**Date:** 2026-11-10 (grilling, Q6; agreed: "ok", to the recommended option 1)

**Question:** how is a redesign, mostly about appearance, tested at the two sizes of decision 002?

**Decision:** **both.** `pytest-textual-snapshot` joins the dev dependencies; each screen has an SVG snapshot at
160×45 and at 80×24, on fixed data with no live model, committed under `tests/tui/__snapshots__/`. The Pilot tests
in `tests/tui/` keep proving what each screen does (skip a cell, edit, retry, accept), carried over as each screen
is rewritten.

- **Why:** a snapshot changes only when the look does, and its diff shows in review; Pilot proves the actions.
- **Not chosen:** Pilot only, checking widgets and classes (a broken layout or a wrong colour passes); snapshots
  only (they prove nothing about the actions).
