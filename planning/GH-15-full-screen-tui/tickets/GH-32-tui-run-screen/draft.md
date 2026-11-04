# Watch a TUI run live, retries and failures included

## Problem

The progress port takes a description string per finished file, and the engine says nothing until a file is done:
a run cannot show which file × locale is being translated, or its retries as they happen.

## The change

- The engine yields two new events, `AtomStarted` and `AttemptRejected` (how many messages, which attempt of how
  many), which the atom writes to LangGraph's stream as they happen.
- `IGenerationProgress` takes one typed event at a time, `on(event)`: `RunStarted`, `JobStarted`, `JobRetrying`,
  `JobDone` (with its `FileResult`), `FileDropped`, `RunFinished`; the handler passes each on (story decision 004,
  decision 001). The console adapter renders what it renders today.
- **Run screen:** the plan's files × locales grid, each cell live (waiting, translating, retry k/n, written,
  partial, failed, ignored, off), a progress bar, and the failures and partial files under **Problems** as they
  arrive; the receipt replaces the grid at the end (decision 002).

## Done when

- [ ] An engine test with the fake model sees started, retrying and done for an atom whose first attempt is rejected.
- [ ] The CLI's `generate` output is unchanged: a test of the console adapter pins its lines before the change.
- [ ] A `Pilot` test watches a run go from waiting to written, through a retry.
