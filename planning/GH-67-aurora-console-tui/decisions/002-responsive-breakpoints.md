# 002: The layout has breakpoints, down to 80×24

**Date:** 2026-11-10 (grilling, Q2; agreed: "ok", to the recommended option 1)

**Question:** what happens in a terminal smaller than v2's design (about 160×45)?

**Decision:** **responsive breakpoints.** At about 120 columns and wider, the full v2 layout. Narrower, the sidebar
becomes an icon rail and the side panels (the plan's inspector, the review's other locales and attempts) move under
the main one. Below 80×24, a notice asks for a larger terminal. Each screen is tested at 160×45 and 80×24.

- **Why:** usable on a laptop terminal at its default size, the full look when there is room; Textual swaps CSS
  classes on resize, so it is a few rules per screen, not a second layout.
- **Not chosen:** one fixed minimum size (nothing shows on a small terminal); one fluid layout with no breakpoints
  (cramped and scrolling at 80 columns).
