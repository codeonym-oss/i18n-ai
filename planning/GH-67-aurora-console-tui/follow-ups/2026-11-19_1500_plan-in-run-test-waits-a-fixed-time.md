---
status: open
from: agent
found-while: GH-84
resolved-by:
---

# A shell test waits a fixed 0.3 s for the plan to show

`test_a_plan_shows_in_run_when_another_section_was_picked_meanwhile` (`tests/tui/test_shell.py`) releases the held
scan, then `await pilot.pause(0.3)` before asserting the plan is on screen. On 2026-11-19 it failed once in a full
`uv run pytest` (503 passed, 1 failed) and passed five times alone: under load, 0.3 s is not always enough.

Left for later: it predates GH-84 and does not touch the model's pick.

Fixing it: wait for the plan rather than for a time, e.g. `settle(pilot)` or a loop on `isinstance(app.screen,
PlanScreen)` with a deadline, as `footed` does in `tests/tui/conftest.py`.
