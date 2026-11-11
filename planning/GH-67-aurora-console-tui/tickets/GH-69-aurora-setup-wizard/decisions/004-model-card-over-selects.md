# 004: The Model step keeps its selects, under one model card

**Date:** 2026-11-11 (ticket pass, Q4; agreed: "ok", to the recommended option 1)

**Question:** how does the Model step show the provider, the model and the key, with 26 providers from LangChain
and a provider's model list running to dozens?

**Decision:** **today's selects, restyled, under one model card.**

- The step holds the provider `Select` (the ready ones first, as today), the model `Select` ("★ recommended"), and
  the key, asked only when it is missing.
- Above them, a card in v2's style: the provider, the model, the key's state ("✓ set (keyring)", "none needed",
  "key needed"). The same card shows in the "This run" panel.

- **Why:** the design's model card without a grid of providers; the fields and their tests stay as they are.
- **Not chosen:** the ready providers as cards beside an "Other provider…" select (two ways to pick one, and cards
  that depend on the machine's keys); all 26 providers as cards (a step of cards nobody uses, cramped at 80
  columns).
