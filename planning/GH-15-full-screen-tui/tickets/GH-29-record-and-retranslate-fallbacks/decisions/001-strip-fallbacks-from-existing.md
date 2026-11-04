# 001: The handler leaves recorded fallbacks out of the existing targets

**Date:** 2026-10-26 (ticket pass, Q1; agreed: "ok", to the recommended option 1)

**Question:** how does the next run translate a recorded fallback again instead of keeping it?

**Decision:** **`GenerateLocalesCommandHandler` removes each recorded fallback from the existing target document
it hands the engine.** To the atom the message is simply missing, so it is translated like a new one. The engine
port, the atom and `reusable_translations` are unchanged.

- **Why:** the narrowest seam; the same in every format and layout; the handler already builds `existing`.
- **Not chosen:** a `retranslate` set on `TranslationJob` (port, atom and their tests changed for what the handler
  can say alone); the record passed to `reusable_translations` (a domain rule about text would learn about a file).
- **Needs:** a way to drop key paths from a `LocaleDocument`.
