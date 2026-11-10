# 004: Each sidebar section is a Textual mode with its own stack

**Date:** 2026-11-10 (grilling, Q4; agreed: "ok", to the recommended option 1)

**Question:** how does navigation work once there is a sidebar, when today one stack pushes setup → plan → run →
review?

**Decision:** **Textual modes, one per section: Home, Run (setup → plan → run, a stack as today), Review.** Each
keeps its stack, so a running generation goes on while the person looks at Home and is there on return. A shared
shell, used by every screen, draws the sidebar, the command bar and the status line. History, Providers and
Settings (out of scope, decision 001) are not shown until their story ships them.

- **Why:** Textual's own tool for sections; a run one can step away from is what gives the sidebar meaning.
- **Not chosen:** one stack with a decorative sidebar (leaving a run ends it); the later sections greyed out as
  "soon" (advertises what does not exist).
