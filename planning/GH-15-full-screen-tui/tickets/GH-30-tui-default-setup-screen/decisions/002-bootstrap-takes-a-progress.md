# 002: `Bootstrap` takes the progress the TUI shows

**Date:** 2026-10-26 (ticket pass, Q2; agreed: "ok", to the recommended option 1)

**Question:** how does a TUI run keep from printing on the terminal Textual draws on?

**Decision:** **`Bootstrap(settings, console, progress=None)`**: given a progress, `di` provides it as
`IGenerationProgress` instead of `RichGenerationProgress`. The TUI gives its own adapter, in `cli/tui/`, and a
`Console(quiet=True)`. Until ticket 4 (#32) the adapter is a progress bar and a line for each file × locale done;
#32 changes it for the typed events.

- **Why:** dishka stays in `di`; the CLI hands over an object of the application's port, which it may import.
- **Not chosen:** raw dishka overrides on `Bootstrap` (the CLI would import dishka and build providers, around the
  "only through the container" contract); the Rich adapter printing to a buffer the TUI scrapes (fragile, and #32
  throws it away).
