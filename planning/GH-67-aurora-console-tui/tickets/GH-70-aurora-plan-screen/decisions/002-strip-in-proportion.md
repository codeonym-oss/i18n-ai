# 002: A cell's strip is its file's messages in proportion to the cell's width

**Date:** 2026-11-11 (ticket pass, Q2; agreed: "ok", to the recommended option 1)

**Question:** what does a cell's strip of messages show, when the scan knows what is to translate and kept, the
record knows the fallbacks, and nothing knows which messages are broken?

**Decision:** **the strip's width is the file's messages, in proportion.** A sky run for the messages to translate,
the cell's recorded fallbacks in amber inside it, a dark run for the kept ones. The legend under the grid has three
entries: to translate, kept, fallback again. A cell off shows its strip muted.

- **Why:** a 14-message file and a 400-message one both read at a glance as a share of the work; v2's look, true at
  any size.
- **Not chosen:** a glyph per message cut at the cell's width, as v2 (a big file shows a full bar whatever its share);
  no strip (loses v2's main visual idea); v2's "broken, again" (nothing tells which messages are broken).
