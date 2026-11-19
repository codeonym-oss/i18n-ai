# 002: The editor's text is checked when it is saved, not as it is typed

**Date:** 2026-11-19 (ticket pass, Q2; taken as recommended after the person asked to "finish all the remaining tasks", no answer given to the question itself)

**Question:** v2 checks the rules live as you type; there is no command that checks without writing (story rule: no
new command). How does the editor check?

**Decision:** **on `enter`, through `SetMessageCommand`.** It checks, then writes only a text that keeps to the
rules (#15 decision 002). Until then the check line shows the rules the record says were broken; after a refused
save, the command's violations, in the error colour; a written one moves to the next fallback and the list updates.

- **Why:** no new command; the check the command makes is the one that counts.
- **Not chosen:** a live check calling the domain's `check` from the TUI (the TUI would reach past the mediator);
  a new check-only query (story rule).
