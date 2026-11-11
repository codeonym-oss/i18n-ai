# Show a TUI run's plan as Aurora cells with an inspector

## Problem

The plan is a stock table of counts; what a cell holds, and why a file does not qualify, takes reading.

## The change

- The files × locales grid as v2's big cells: each with its state (new, fill, up to date, off) and a strip of its
  messages, coloured from the theme.
- An inspector beside the grid for the cell under the cursor: its counts, its fallbacks, its path; below the grid
  at narrow sizes (story decision 002).
- The totals bar. Turning a cell, a row or a column off works as today (#15 decision 005).
- v2's lanes bar is not part of it (decision 001).

## Done when

- [ ] The plan's `Pilot` tests carried over: a cell turned off is not written.
- [ ] Snapshots at 160×45 and 80×24.
