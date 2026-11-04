# 007: The TUI lives in `i18n_ai/cli/tui/`

**Date:** 2026-10-26 (grilling, Q7; agreed: "ok", to the recommended option 1)

**Question:** where does the TUI's code live?

**Decision:** **`i18n_ai/cli/tui/`, a subpackage of the CLI.** The root callback opens it (decision 006), and
`i18n-ai tui` names it explicitly. It reuses `cli/common` (the runner, preset detection) and the mediator queries
the wizard uses. The import-linter layers are unchanged; a new forbidden contract keeps `textual` inside
`i18n_ai.cli.tui`. The shell story adds `cli/shell/` the same way.

- **Why:** nothing that exists moves; each later mode is one more subpackage.
- **Not chosen:** renaming `cli` into `presentation/{cli,tui,shell}` as acli-py has (a refactor no screen needs);
  a top-level `tui` layer beside `cli` (`cli` could not open it without moving shared pieces down a layer).
