# 002: Accept is a command of its own, which changes only the record

**Date:** 2026-11-04 (ticket pass, Q2; agreed: "1, go with your recommendation")

**Question:** accept keeps a fallback's text and takes it out of the record (story decision 008); the TUI writes
nothing itself (story rule: through the mediator). Which intent carries it?

**Decision:** **an `AcceptFallbacksCommand`:** the tree and the fallbacks to accept, which leave the record. No
locale file is read or written. It takes several at once. The ticket has three intents, not the draft's two: set
a message, retry fallbacks, accept fallbacks.

- **Why:** accept changes the record only; a command that says so is clearer than a write that changes nothing,
  and the review accepts several in one go.
- **Not chosen:** set-message with the current text (rewrites the file for nothing, and accept is only a
  convention); a flag on set-message (two behaviours behind one name).
