# 010: Five tickets, each a screen with the change it needs

**Date:** 2026-10-26 (grilling, Q10; agreed: "ok", to the recommended option 1)

**Question:** how does the story split into tickets, and in what order do they ship?

**Decision:** **five vertical slices, in this order:**

1. **Record the fallbacks and translate them again** (decisions 008, 009): the CLI alone, no TUI yet.
2. **The TUI as the default mode, and its setup screen** (006, 007): Textual a dependency, the import contract,
   `i18n-ai` opening the setup form, running the generation and showing the receipt; the `Ctrl+P` palette and key
   bindings.
3. **The plan screen, and the skip pairs on the command** (005).
4. **The run screen, and the typed progress events** (004).
5. **The review screen, and the set-message and retry-messages intents** (002, 003), reading ticket 1's record.

- **Why:** each ticket after the first shows something; each backend change lands with its first user, and is
  reviewed beside the screen that explains it.
- **Not chosen:** the backend changes first as four tickets of their own (eight tickets, four before a screen);
  the review's intents split from the review screen (can still happen in ticket 5's own pass if it is too big).
