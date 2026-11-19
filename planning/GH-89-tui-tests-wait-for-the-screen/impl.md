# GH-89: implementation plan

Planned 2026-11-19 against `main` at d97a738. No decision of its own: the draft says how to fix it.

## Read first

- `tests/support/tui.py`: `settle`, `ended`, `planning`, `scripted`, `post`.
- `tests/tui/conftest.py` (`snap`, `footed`), `tests/tui/test_run.py` (`showing`), the fixed `pause(0.2)`/`pause(0.3)`
  waits in `tests/tui/test_tui.py` and `tests/tui/test_shell.py`.
- Textual 8.2.8: `Pilot.pause` waits one pass over the widgets' messages; `Widget.is_mounted`.

## Steps

1. **A way to see it fail.** A scratch pytest plugin (not kept) makes `Widget._compose` sleep up to 100 ms at random.
   → check: the TUI tests fail on `main` (7 of 100).
2. **`drawn` and `arrived`** in `tests/support/tui.py`; `settle` ends on `drawn` and goes round again while a worker
   is left. → check: ruff and mypy clean.
3. **The helpers and tests use them:** `ended`, `planning`, `scripted`, `post`, `showing`, the snapshot fixture, and
   every fixed wait before an assertion. → check: the TUI tests pass, and under the plugin.

## Review

Steps 1–3 done. Correction: under the plugin one test still failed on the branch,
`test_a_run_writes_the_targets_and_says_how_to_run_it_again`: its feed's top line was the last file's, not "run
finished". The cause was in the app: `TuiProgress` posts the events to the run screen as messages, and `_run` in
`src/i18n_ai/cli/tui/setup.py` called `show_receipt` (and `halted`, `stopped`) directly, ahead of events still queued.
They now go through `screen.call_later`, behind them.
