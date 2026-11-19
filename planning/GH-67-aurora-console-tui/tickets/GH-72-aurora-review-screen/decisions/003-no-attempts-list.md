# 003: No attempts list: the model's card is its last attempt

**Date:** 2026-11-19 (ticket pass, Q3; taken as recommended after the person asked to "finish all the remaining tasks", no answer given to the question itself)

**Question:** v2 lists every attempt with its reason; the record keeps only the last rejected translation and the
rules it broke (#15 decision 008). What shows the attempts?

**Decision:** **nothing more than the record holds.** The model's card is titled `MODEL · last attempt` and shows
the rejected text and, under it, each problem's message. No attempts column.

- **Why:** a history of attempts would change the record (a new store shape), outside this story (decision 001).
- **Not chosen:** keeping the record's every attempt (the record and `generate` change).
