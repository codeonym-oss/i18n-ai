# 001: The snapshots use syrupy and Textual's own SVG export, not pytest-textual-snapshot

**Date:** 2026-11-10 (ticket pass, Q1; agreed: "ok", to the recommended option 1)

**Question:** how are the SVG snapshots of story decision 006 taken, when `pytest-textual-snapshot` cannot be
installed?

**Found:** `pytest-textual-snapshot` 1.1.0, its latest (January 2025), pins `syrupy==4.8.0`, which requires
`pytest<9`; the project is on pytest 9.2.0.

**Decision:** **a small fixture of our own on syrupy 6.1.1** (requires `pytest>=8`, released 2026-09-13). In
`tests/tui/conftest.py`, a fixture runs the app with `run_test(size=…)`, takes `app.export_screenshot()` (Textual's
SVG export) and compares it through syrupy's `SingleFileSnapshotExtension` as `.svg`; `--snapshot-update`
refreshes them. One dev dependency, `syrupy`, in place of the plugin.

- **Changes story decision 006** in its tool only: the snapshots, their sizes and their place stay as decided.
- **Why:** the same check, with Textual's own export; pytest stays current.
- **Not chosen:** pytest below 9 for the plugin (a step back on a core tool); a hand-rolled compare-and-update
  (what syrupy already does).
