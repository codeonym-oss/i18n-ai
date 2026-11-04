# Plan a TUI run as a files × locales grid, with single cells turned off

## Problem

Between setup and run, the TUI should show what the run will do, and let the person leave parts out. The precheck
(`ScanLocaleTreeQuery`) already gives each file × locale's counts, but `GenerateLocalesCommand` can only leave out
a whole locale or a whole file. The precheck also counts a recorded fallback as reusable, though the run translates
it again.

## The change

- `GenerateLocalesCommand` takes a set of skipped (file, locale) pairs, passed on to the engine, which sends no job
  for them: a skipped cell costs no model call, and the receipt does not list it (story decision 005, decision 002).
- The precheck reads the fallback record, so a recorded fallback counts as to translate (decision 003).
- **Setup → plan → run:** the setup's button becomes **Plan**; the plan screen's **Run** is the go-ahead, and **b**
  goes back to the form (decision 001).
- **Plan screen:** files × locales as a table, each cell **new N**, **fill N**, **up to date** or **off**; the files
  that do not qualify listed with their reason; a total that follows the cells. **space**, **r** and **c** turn a
  cell, a row or a column off or on (decision 005). A full row becomes `--exclude`, a full column leaves the
  targets, single cells go to the skip set.
- "To run it again" carries the `--exclude` flags; when single cells were off, a line says the command runs them
  too (decision 004).

## Out of scope

- A CLI `--skip` flag (story decision 005).

## Done when

- [ ] A handler test: a skipped pair is never sent to the engine, and the other jobs of its file and locale are.
- [ ] A precheck test: a recorded fallback counts as to translate.
- [ ] A `Pilot` test turns one cell off on an `examples/` tree, runs, and finds that file × locale not written.
