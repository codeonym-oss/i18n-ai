# 003: One Aurora theme, one shared stylesheet, one widget kit

**Date:** 2026-11-10 (grilling, Q3; agreed: "ok", to the recommended option 1)

**Question:** how is the v2 look defined and shared between the screens?

**Decision:** **one source for the look.**

- An `aurora` Textual `Theme` holds the palette tokens: background #08070D, violet #A99BFF, mint #54E1B8,
  amber #FFC46B, coral #FF7E93, sky #71B7FF, and the surfaces.
- `cli/tui/aurora.tcss` holds the shared rules: panels, cards, chips, the status line.
- `cli/tui/kit/` holds the widgets every screen reuses: the titled card, the KPI tile, the status chip, the heat
  strip, the key hints.
- Screens keep only their own layout CSS. Dark only; Textual's stock themes leave the palette.

- **Why:** a colour changes in one place, and the shared widgets are what make six screens read as one app.
- **Not chosen:** a light variant too (two palettes to tune, no light design yet; a follow-up when there is one);
  per-screen CSS with hard-coded colours (the same values copied six times).
