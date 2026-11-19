# 002: What each group holds, and what choosing one does

**Date:** 2026-11-19 (ticket pass, Q2; taken as recommended after the person asked to "finish all the remaining tasks", no answer given to the question itself)

**Question:** what are the commands, the locales and the files, and what does choosing a locale or a file do?

**Decision:**

- **Commands (`>`):** the sections (Home `ctrl+o`, Run `ctrl+n`, Review `v`), the screen's own commands as the
  app lists them today (`get_system_commands`: Plan, Run, Back to setup, Review fallbacks), and Quit `q`. Textual's
  stock ones (themes, keys, screenshot) are gone.
- **Go to (`@`):** the target locales of the tree Home shows (its scan). Choosing one opens Run, the setup's targets
  step, with that locale picked: a run into it. A run already under way is only shown.
- **Files (`#`):** the source files of that tree. Choosing one opens Home with that file's coverage column lit.

- **Why:** "go to" a locale is most often to translate into it; a file is seen by its coverage on Home. Nothing new
  underneath: the scan Home already sends.
- **Not chosen:** a locale opening Home's row (Home has no row to focus); a file starting a run of that file alone
  (the setup has no file filter to set).
