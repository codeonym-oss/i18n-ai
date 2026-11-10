# 007: Six tickets, the shell and Home first, then a screen each

**Date:** 2026-11-10 (grilling, Q7; agreed: "ok", to the recommended option 1)

**Question:** how does the story split into tickets, and in what order do they ship?

**Decision:** **six tickets, in this order.** After each one the app runs; a screen not yet redone keeps its current
look inside the new shell.

1. **The shell, the theme, the kit and Home:** the `aurora` theme, `aurora.tcss`, `kit/` (decision 003); the modes,
   sidebar, command bar with the tree switcher, status line (004); the breakpoints (002); the snapshot setup (006);
   Home (005).
2. **The setup wizard,** in the Run mode.
3. **The plan screen:** the big cells with their strips, the inspector.
4. **The run screen:** the progress, the events, the pop-up notice; no time left, no lanes (001).
5. **The review screen:** the three-way comparison, the editor, the attempts.
6. **The command palette:** the `>`, `@` and `#` prefixes; Textual's stock themes gone.

- **Why:** each ticket is one screen, built and checked on its own; the first is the smallest piece that shows the
  new app, and Home proves the kit.
- **Not chosen:** the shell and Home as two tickets (a first pull request with nothing to see but the frame); the
  palette folded into ticket 1 (the largest ticket larger).
- **Left to the ticket passes:** the editor's live check (ticket 5), how far "other locales" goes on the tree alone
  (5), how the palette's prefixes plug into Textual's command providers (6).
