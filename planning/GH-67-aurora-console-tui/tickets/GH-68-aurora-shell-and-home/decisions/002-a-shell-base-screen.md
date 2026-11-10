# 002: Every screen is a `ShellScreen`, filling its body

**Date:** 2026-11-10 (ticket pass, Q2; agreed: "ok", to the recommended option 1)

**Question:** how does every screen share the sidebar, the command bar and the status line, when Textual has no
app-level widgets that persist across screens?

**Decision:** **a base screen, `ShellScreen`, in `cli/tui/kit/shell.py`.** Its `compose` yields the sidebar, the
command bar, a `#body` container filled by the subclass's `body()`, and the status line; it also sets the
breakpoint classes on resize (story decision 002). Setup, plan, run and review move their `compose` to `body` and
become subclasses, their contents unchanged; `ConfirmScreen` and `EditScreen` stay modals above it.

- **Why:** one class; tickets 2–6 only fill `body()`; the frame cannot drift between screens.
- **Not chosen:** a `Shell(body)` widget each screen wraps itself in (the wrapping repeated, resizing in a widget);
  the shell on Home alone for now (breaks the story's rule that the whole app runs inside it after each ticket).
