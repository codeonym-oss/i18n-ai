# 004: The run bar counts messages, agents and calls; the status line the cells on

**Date:** 2026-11-11 (ticket pass, Q4; agreed: "ok", to the recommended option 1)

**Question:** what does the totals bar say, when v2's "11 jobs · 6 batches of ≤40" uses a word `CONTEXT.md` avoids?

**Decision:** **"THE RUN · 47 messages · 4 agents · 5 calls of ≤40", then the key hints** ("a cell space · row r ·
column c"). The calls are, over the cells on, the sum of ⌈to translate ÷ batch size⌉: the first attempt's calls, as
an atom batches its messages (`infra/adapters/langgraph/atom.py`), with the batch size from the settings. The status
line says "PLAN · 3 of 4 cells on" and the cells off ("common.json → de off"). The files left out are v2's dashed
note under the grid ("left out · meta.json — it looks like data").

- **Why:** what a run costs, seen before ⌃R, in the project's words; no new query.
- **Not chosen:** no calls (simpler, but hides the cost); v2's "jobs" and "batches" (`CONTEXT.md` says agent).
