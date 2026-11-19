# GH-84: implementation plan

Planned 2026-11-19 against `main` at 7a5557a. No decision of its own: the follow-up says how to fix it.

## Read first

- `src/i18n_ai/cli/tui/setup.py`: `_list_models`, `_give_key` (its last line), `_fill`.
- Tests: `tests/tui/test_wizard.py` (`test_the_model_card_says_the_keys_state`), `tests/tui/test_run.py`
  (`test_ctrl_c_stops_the_run_and_keeps_what_is_written`, its re-pick after Back).

## Steps

1. **The test in its natural order.** Pick the model, then give the key. → check: it fails (the card reads
   `openai / …`).
2. **`_list_models(provider, keep=False)`:** with `keep`, the model picked before is the default when the new list
   has it; `_give_key` passes `keep=True`; a provider picked anew does not. → check: the test passes.
3. **The run's stop test** asserts the model is still picked after Back, and no longer picks it again. → check:
   `tests/tui/test_run.py` passes.

## Review

Steps 1–3 done as planned (step 1 seen failing first). `uv run pytest`: see the PR.
