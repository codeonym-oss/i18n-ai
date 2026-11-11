# 003: The grid is focusable cell widgets in a view that scrolls

**Date:** 2026-11-11 (ticket pass, Q3; agreed: "ok", to the recommended option 1)

**Question:** what is the plan's grid built from: cell widgets as v2 draws them, or the `DataTable` it uses today?

**Decision:** **a `PlanCell` per file × locale, in `kit/`, laid out in a grid inside a view that scrolls.** A cell's
border takes its state's colour, and a heavier one when it has the focus. The file names are the first column, the
locales the header row. The arrows move the focus from cell to cell and the view scrolls to it; Space, `r` and `c`
act on the focused cell, as today. At the narrow size (80×24) the cells are shorter: the tag and the number on one
line, the strip under it. `JobGrid` stays for the run screen until GH-71.

- **Why:** the big cells are what the ticket is; focus and scrolling are short in Textual.
- **Not chosen:** the `DataTable` with taller rows and styled text (no borders, it reads as a table); cell widgets
  that shrink to fit with no scrolling (breaks past a few files or locales).
