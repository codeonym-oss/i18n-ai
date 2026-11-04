# 005: The plan is one table of cells, toggled by cell, row or column

**Date:** 2026-10-29 (ticket pass, Q5; agreed: "ok", to the recommended option 1)

**Question:** how is the plan grid laid out, and how are its cells turned off?

**Decision:** **one Textual `DataTable` with a cell cursor:** a row per qualifying file, a column per target.

```
┌ i18n-ai ─ plan ─────────────────────────────────┐
│ File              fr          de        es      │
│ common.json       fill 3      new 12    off     │
│ auth/login.json   up to date  new 8     new 8   │
│ Left out: legacy.txt — not a locale document    │
│ 4 jobs · 31 messages                            │
└ space cell  r row  c column  ^r run  b back ────┘
```

- A cell is **new N** (no target file), **fill N** (an existing target, N to translate), **up to date** (nothing to
  translate; the draft's "skip", renamed so it is not read as "off") or **off**.
- **space** toggles the cell under the cursor; **r** and **c** its row or column: all off, or all on again when all
  are off already.
- Files that do not qualify are listed under the table with their reason. The total line follows the cells; Run is
  refused when every cell is off.

- **Why:** the grid the issue and the story describe; `DataTable` has the cursor, the scrolling and the narrow
  terminal handled.
- **Not chosen:** a checklist per file (no column at a glance; a whole locale off means visiting every file).
