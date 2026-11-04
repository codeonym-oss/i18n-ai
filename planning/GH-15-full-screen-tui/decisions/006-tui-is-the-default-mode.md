# 006: The TUI is the default mode; the shell is a story of its own

**Date:** 2026-10-26 (grilling, Q6; the person: "the CLI will offer two modes, TUI (default) and SHELL (explicit),
tui opens the tui interface! shell opens an interactive shell (check acli-py)"; then "ok" to the reading below and
to option 2)

**Question:** how does the TUI sit beside the CLI, and is the shell part of this story?

**Decision:**

- **`i18n-ai` alone, at a terminal, opens the TUI**, in place of today's guided wizard. Off a terminal (piped, CI)
  it prints the help, as today.
- **`i18n-ai shell` is the explicit second mode,** as in acli-py: every command at a prompt, with completion. It is
  **a story of its own**, a new issue, planned in its own pass; not part of #15.
- **The commands stay the scripted mode.** `generate` and the others are unchanged; #13's line-by-line prompts
  still ask what a `generate` at a terminal is missing.
- **Textual is a regular dependency,** as in acli-py: a default mode cannot sit behind an extra. This drops #15's
  `i18n-ai[tui]` extra and its "nothing imports Textual without the extra" acceptance check.

- **Why:** the person's direction, following acli-py's two interactive modes. The shell shares almost nothing with
  the four screens (another library, no progress or review work), so each story ships without waiting on the other.
- **Not chosen:** the shell inside this story (two more tickets with nothing in common with the screens).
- **Supersedes 001 in part:** its "the optional `i18n-ai[tui]` extra"; the issue's text is updated to match.
