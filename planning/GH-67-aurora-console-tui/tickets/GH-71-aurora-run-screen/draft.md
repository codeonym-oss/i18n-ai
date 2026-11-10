# Show a TUI run live on the Aurora run screen

## Problem

The run screen is a stock grid and a log; a retry or a dropped file is easy to miss.

## The change

- v2's run screen on the typed progress events there are today (#15 decision 004): the overall progress, each job
  as a card with its state and attempts, the event feed, a pop-up notice when a file is dropped or the run ends.
- The receipt at the end, leading to Review when there are fallbacks.
- Without the time left, the throughput sparkline and the per-call lanes (story decision 001).

## Done when

- [ ] The run's `Pilot` tests carried over: a retry and a dropped file show as they happen.
- [ ] Snapshots at 160×45 and 80×24, on a scripted series of events.
