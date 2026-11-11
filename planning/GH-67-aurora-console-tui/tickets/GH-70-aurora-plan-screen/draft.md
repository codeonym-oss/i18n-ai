# Show a TUI run's plan as Aurora cells with an inspector

## Problem

The plan is a stock table of counts; what a cell holds, and why a file does not qualify, takes reading.

## The change

- The files × locales grid as v2's big cells, focusable and scrolling, the arrows moving between them (decision
  003): each with its state (new, fill, up to date, off), its messages to translate, and a strip of the file's
  messages in proportion: to translate, its recorded fallbacks, kept (decision 002), coloured from the theme.
- An inspector beside the grid for the focused cell: its state and counts, its target path, and its recorded
  fallbacks with their keys and source texts (decision 001); below the grid at narrow sizes (story decision 002).
- The run bar: the messages, the agents and the model calls of the cells on, with the keys; the status line says
  how many cells are on and which are off; the files left out as a note under the grid (decision 004).
- Turning a cell, a row or a column off works as today (#15 decision 005).

## Not part of it

- v2's lanes bar (story decision 001).
- v2's Grid / Messages / Tree views and a list of every message with its reason: the scan gives counts, not
  messages, and the story adds no query (decision 001).

## Done when

- [ ] The plan's `Pilot` tests carried over: a cell turned off is not written.
- [ ] Snapshots at 160×45 and 80×24.
