# Open a full-screen TUI by default, starting with its setup screen

## Problem

`i18n-ai` alone, at a terminal, starts the line-by-line prompts. The story makes a full-screen TUI the default
mode (story decision 006); this ticket lays it down with its first screen.

## The change

- `textual` becomes a dependency. The TUI lives in `i18n_ai/cli/tui/`, and an import-linter contract keeps `textual`
  inside it (decision 007).
- `i18n-ai` at a terminal opens the TUI; off a terminal it prints the help, as today. `i18n-ai tui` opens it
  explicitly.
- **Setup screen:** tree, source, targets (multi-select with search), output, provider, model and key, from the
  queries the prompts use, with the last answers as defaults and the detected preset shown. A missing provider or key
  is handled as the prompts handle it.
- **Run it:** the setup sends `GenerateLocalesCommand` (no strict option, decision 003), then shows the receipt.
  Plan, live run and review come in tickets 3 to 5.
- `Ctrl+P` opens a command palette; every action has a key binding.

## Out of scope

- The plan grid, live progress and the review (tickets 3–5); `i18n-ai shell` (its own story).

## Done when

- [ ] A `Pilot` test fills the setup on an `examples/` tree with the fake model, runs it, and sees the receipt; the
      files are written.
- [ ] `lint-imports` fails if a module outside `i18n_ai.cli.tui` imports `textual`.
- [ ] `i18n-ai` piped, or with `CI=true`, prints the help; `i18n-ai generate` with every argument is unchanged.

Settled in the ticket pass: the shared setup pieces move to `cli/common/setup.py` (decision 001); `Bootstrap`
takes the TUI's progress, so nothing prints on its screen (002); the setup is one form (003); Run is the go-ahead,
and the receipt says how to run it again (004).
