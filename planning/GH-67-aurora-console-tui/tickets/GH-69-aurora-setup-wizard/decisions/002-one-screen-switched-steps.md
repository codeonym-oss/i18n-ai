# 002: One screen, its steps switched in place, none gated

**Date:** 2026-11-11 (ticket pass, Q2; agreed: "ok", to the recommended option 1)

**Question:** how does the wizard move between its three steps (decision 001)?

**Decision:** **one `SetupScreen`, its steps the panes of a `ContentSwitcher`, every field mounted all the time.**

- The header shows the three step chips (✓ done, ● current); a chip clicked opens its step.
- Each step ends with **Continue** (Enter on it); **Esc** goes back a step; **Tab** keeps moving focus inside the
  step.
- **⌃R** plans from any step; when something is missing, it opens the first step that lacks it and says what.
- No step is gated: Model may be opened before Targets. A field still waits on what it depends on, as today.
- The tests keep setting the widgets by id across the hidden steps; snapshots show each step.

- **Why:** the run's state stays in one screen, as today; the Run stack keeps the shape decision 004 gave it; the
  carried-over tests barely change.
- **Not chosen:** a screen per step pushed on the Run stack (the state handed between screens, three stack entries,
  every test walking the steps); gated steps (stricter than today's form, which takes the fields in any order).
