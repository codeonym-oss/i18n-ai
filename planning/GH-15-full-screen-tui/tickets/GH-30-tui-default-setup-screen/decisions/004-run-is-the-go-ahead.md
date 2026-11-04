# 004: Run is the go-ahead; the receipt says how to run it again

**Date:** 2026-10-26 (ticket pass, Q4; agreed: "ok", to the recommended option 1)

**Question:** what happens between pressing Run and the receipt?

**Decision:**

- **Run is the go-ahead:** no second confirmation; the form and its files · locales line already say what will
  happen. The answers are remembered, as the prompts remember them.
- **One dialog, when it is needed:** "Install `<package>`?" when the provider's package is missing; no means back to
  the form.
- **A run screen:** a progress bar and a line for each file × locale done (through decision 002's adapter; #32
  makes it live).
- **Then the receipt:** the per-file table the CLI prints, and **"To run it again: `i18n-ai generate …`"**, from
  `command_line`; keys to go back to the setup or quit.

- **Why:** the go-ahead once, where the person already sees everything; the command line keeps the bridge to
  scripts and CI that the prompts give.
- **Not chosen:** a confirmation dialog before each run (says again what the form shows); no command line (loses
  that bridge).
