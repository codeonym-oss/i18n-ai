# A full-screen TUI: set up, run and review a generation

## Goal

The line-by-line prompts (#13) get a run started. A large tree, though, with dozens of files and many locales,
benefits from seeing everything at once: what will be translated, what is happening, and what failed and why. This
story makes a full-screen TUI, built with [Textual](https://textual.textualize.io/), i18n-ai's default mode:
`i18n-ai` alone, at a terminal, opens it (decision 006).

## What it delivers

- **Setup screen:** the tree, source, targets (multi-select with search), output, then provider, model and key: the
  prompts' steps, as a form, with the last answers as defaults.
- **Plan screen:** files × locales as a grid. Each cell shows new, fill or skip and its message count; a cell, a
  row or a column can be turned off before the run (decision 005).
- **Run screen:** each file × locale live, its retries and failures as they happen (decision 004).
- **Review screen:** each message left in its source text (a fallback), with the source, the model's last rejected
  translation and the rule it broke. **Edit** it (checked against the rules, then written), **retry** it, or
  **accept** it (decision 002).
- `Ctrl+P` opens a command palette; every action has a key binding; the screens adapt to the terminal's size.

Along the way, the CLI gains too: a generation records the fallbacks it leaves, in `.i18n-ai-fallbacks.json` beside
the targets, and the next run translates them again instead of keeping them for good (decisions 008, 009). Today a
fallback breaks no rule, so it is kept by every later run.

## Rules every ticket keeps

- **Through the mediator:** the TUI sends the same queries and commands as the CLI; no generation logic lives in
  `cli/tui`.
- **One generation model:** files are written as they are translated, in the TUI as in the CLI. The review fixes what
  is on disk; nothing waits in memory for it (decision 002). The TUI has no strict option (decision 003).
- **Layers:** the TUI lives in `i18n_ai/cli/tui/`; a contract keeps `textual` inside it, and the domain and the
  application stay free of it (decision 007).
- **The CLI's behaviour holds:** `generate` and the other commands keep their output and options, apart from
  translating recorded fallbacks again.
- **Tests:** each screen through Textual's `Pilot`, on the `examples/` trees with the fake model.

## Tickets, in the order they ship

1. **Record the fallbacks, and translate them again** (decisions 008, 009): the CLI alone.
2. **The TUI as the default mode, and its setup screen** (decisions 006, 007): from here on a TUI run works from
   setup to receipt.
3. **The plan screen, and turning single cells off** (decision 005).
4. **The run screen, and typed progress events** (decision 004).
5. **The review screen: edit, retry or accept a fallback** (decisions 002, 003).

## Not part of it

- **`i18n-ai shell`,** every command at a prompt with completion, as in acli-py: a story of its own (decision 006).
- **A CLI `--skip file:locale` flag,** to repeat a TUI run with single cells off (decision 005).
- **An `i18n-ai review` command** using the review's intents outside the TUI (decision 002).

## Done when

- [ ] `i18n-ai` at a terminal opens the TUI, and a full run on an `examples/` tree with the fake model goes from setup
      through plan and run to review, and writes.
- [ ] Textual's `Pilot` tests cover each screen.
- [ ] A fallback left by a CLI run shows in the TUI's review, and is translated again by the next run.
