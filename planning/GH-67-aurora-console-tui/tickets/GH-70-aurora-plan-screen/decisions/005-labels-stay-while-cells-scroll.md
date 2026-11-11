# 005: The file names and the locale headers stay in view while the cells scroll

**Date:** 2026-11-11 (while building, after decision 003; agreed: "ok", to the recommended option 1)

**Question:** decision 003 puts the cells in a view that scrolls; with the file names and the locale headers in the
same view, they scroll away on a small terminal. Do they stay?

**Decision:** **both stay, like a spreadsheet's frozen row and column.** The locale headers are a strip above the
cells, the file names a column beside them, each outside the cells' scrolling view and kept at its offsets: the
header strip follows its `scroll_x`, the file column its `scroll_y`. A snapshot after scrolling pins it.

- **Why:** at 80 columns three or more locales already scroll sideways, and then the file names went off screen;
  the `DataTable` gave this for free, and the cells should not lose it.
- **Not chosen:** as built, the inspector's title naming the cell (bearings lost once the grid scrolls); only the
  header row fixed (the file names still go at 80 columns).
