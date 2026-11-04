---
status: open
from: agent
found-while: GH-33
resolved-by:
---

# `generate` keeps stale fallback record entries for good

`GenerateLocalesCommandHandler.handle` (`src/i18n_ai/application/intents/locale/commands/generate_locales/handler.py`,
the `finally` block) rewrites a target's record entries only when it writes that target. An entry whose source
message was deleted, whose source file was removed, or whose locale is no longer generated stays in
`.i18n-ai-fallbacks.json` forever, and is committed with the locales.

Left for later because the story keeps the CLI's behaviour as it is, but for translating recorded fallbacks again
(GH-15's rules); GH-33 shows such entries as stale and lets the review accept them (GH-33 decision 007).

Fixing it: when `generate` writes a target, drop that target's entries whose path is no longer in its schema; and
decide whether entries for a file or locale outside the run are dropped (they may only be excluded from this run).
