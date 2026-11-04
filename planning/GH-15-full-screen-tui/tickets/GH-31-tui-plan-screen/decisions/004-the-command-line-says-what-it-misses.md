# 004: The command line keeps rows and columns, and says when single cells were off

**Date:** 2026-10-29 (ticket pass, Q4; agreed: "ok", to the recommended option 1)

**Question:** what does the receipt's "To run it again" say when the plan turned cells off?

**Decision:** **a file whose every cell is off is `--exclude <name>`, a locale whose every cell is off leaves `-t`;
single cells left are not in the command, and a line under it says so**: "2 single cells were off; this command
runs them too."

- **Why:** the command stays as close to the run as the CLI can say, and is honest where it can't (story
  decision 005: no `--skip` flag in this story).
- **Not chosen:** no command whenever a single cell is off (the bridge to scripts lost in its most common case); a
  `--skip file:locale` flag now (supersedes story decision 005, and adds an option, its parsing and docs here).
