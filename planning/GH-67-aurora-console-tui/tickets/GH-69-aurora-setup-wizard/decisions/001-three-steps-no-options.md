# 001: Three steps, Tree, Targets and Model; no Options step

**Date:** 2026-11-11 (ticket pass, Q1; agreed: "ok", to the recommended option 1)

**Question:** which steps does the wizard have, when v2's design shows four (Tree, Targets, Model, Options) and the
TUI's form today has no options at all?

**Decision:** **three steps, holding today's fields and no others.**

1. **Tree:** the tree (or its typed path), the source when the scan cannot tell it, the output.
2. **Targets:** the locale cards.
3. **Model:** the provider, the model, the key.

The "This run" panel shows beside every step. The run keeps the settings' options, as today.

- **Why:** the ticket is a restyle with "the same result as the form today"; options in the TUI are a feature of
  their own, with their own tests and the repeated command line's flags.
- **Not chosen:** v2's four steps with overwrite, classify and context (more than the form does today; strict stays
  out anyway, GH-15 decision 003); one page with step headers and no stepping (not the wizard of the design).
