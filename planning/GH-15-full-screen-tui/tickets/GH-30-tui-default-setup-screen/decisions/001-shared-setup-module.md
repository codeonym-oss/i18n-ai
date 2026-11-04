# 001: The setup's shared pieces move to `cli/common/setup.py`

**Date:** 2026-10-26 (ticket pass, Q1; agreed: "ok", to the recommended option 1)

**Question:** how does the setup screen share the wizard's work without copying it?

**Found:** the choices (trees with the preset first, locales "in the tree", providers by key and install state,
models) are built inside the `Wizard`'s prompt methods; the order of the steps and their effects (preset, source
when unknown, precheck, provider install, answers remembered, options from the settings) are inside
`cli/handlers/generate.py::generate.flow`.

**Decision:** **a module `cli/common/setup.py` holds what both need:** the choice builders (as `Choice` lists with
their defaults from the last answers), the tree request with its preset, the `GenerationOptions` from the settings,
and the `Answers` to remember. The `Wizard` asks them one by one, as today; the TUI shows them as a form's fields.
The refactor comes first in the ticket, under the existing CLI and interactive tests.

- **Why:** the only way to a real form with one source for the choices.
- **Not chosen:** the TUI as a `Prompter` running `generate.flow` in dialogs (one question at a time, not a form);
  the TUI building its own choices from the queries (about 80 lines copied, then drifting).
