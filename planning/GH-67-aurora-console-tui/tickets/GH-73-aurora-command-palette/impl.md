# GH-73: implementation plan

Planned 2026-11-19 against `main` after GH-72 (#82). Ticket decisions 001–002; story decisions 001–006 (one look in
`aurora.tcss` and `kit/`, snapshots at 160×45 and 80×24, nothing new underneath).

## Read first

- `src/i18n_ai/cli/tui/app.py`: `get_system_commands`, the section actions, `tree_request`.
- `src/i18n_ai/cli/tui/kit/shell.py`: the command bar's `#palette` click (`action_command_palette`).
- `src/i18n_ai/cli/tui/home.py`: `_load` (the scan), `_coverage` (the heatmap's columns).
- `src/i18n_ai/cli/tui/setup.py`: `_scan` (where `_checked` is set), `_show_targets`, `step`.
- Textual: `textual.fuzzy.Matcher`, `OptionList` with disabled options as headers.

## The design, point by point

- **`kit/palette.py`:** `PaletteEntry(group, glyph, title, hint, key, run)`; `PaletteScreen(ModalScreen[PaletteEntry |
  None])` with `Input#palette-input`, `OptionList#palette-results`, a keys line. `PREFIXES = {">": "Commands",
  "@": "Go to", "#": "Files"}`. Each change: the group the prefix keeps, the entries whose title matches (all when
  the search is empty), best first within each group, the groups in that order, a disabled header before each.
  `↑`/`↓` in the input move the list; `enter` dismisses with the highlighted entry; `escape` with None.
- **The app:** `action_command_palette` (a worker): builds the entries — the commands (sections, the screen's
  `get_system_commands` without Textual's, Quit), then, when there is a tree, its scan's target locales and
  source files — and pushes the palette; the chosen entry's `run` is called once it closes.
  `get_system_commands` no longer yields Textual's.
- **A locale:** `I18nAiApp.run_into(code)`: Run's mode; when its stack is the setup alone, `SetupScreen.pick(code)`:
  added to the picks (kept for after the scan when it has not ended), the targets step shown.
- **A file:** `I18nAiApp.show_file(name)`: Home's mode, `HomeScreen.spotlight(name)`: its coverage column's head and
  cells get `-lit`; another file or none clears it.
- **The look:** `aurora.tcss`, "The palette": a box 76 wide (the screen's width less 4 when narrow), its border
  primary, the headers muted and bold, the hint muted, the key right.

## Steps

1. **The palette screen.** → check: `tests/tui/test_palette.py`: on a fake set of entries, `>` keeps the commands,
   `@` the locales, `#` the files, no prefix all three with their headers; a search narrows; `enter` returns the
   highlighted entry, `escape` None.
2. **The app's entries; Textual's gone.** → check: `ctrl+p` on Home lists Home, Run, Review, Quit, the tree's `fr`
   and its two files; no "Theme" or "Keys"; `>run` then enter does what `ctrl+n` does.
3. **A locale chosen.** → check: `@de` then enter opens the setup's targets with `de` picked.
4. **A file chosen.** → check: `#login` then enter shows Home with `auth/login.json`'s column lit.
5. **Snapshots** at 160×45 and 80×24 (`test_palette`). → check: nothing cut at 80×24.
6. **Docs:** getting started's `Ctrl+P` sentence. → check: the prefixes named.

## Risks

- The palette's entries need the tree's scan: a refusal leaves the commands alone.
- A setup not yet scanned when a locale is chosen: the pick waits for the scan.

## Corrections while building

- `action_command_palette` stays a plain action (Textual's own is one; a worker's signature breaks the override)
  and starts the `_palette` worker that scans and pushes the screen.
- The section commands' keys come from a table in `app.py` (`_SECTIONS`); a screen's own commands take their key
  from the screen's `BINDINGS` by the callback's action name.
- `tests/tui/conftest.py` `footed` reads the footer of the screen under a pop-up: the palette has none of its own.
- `test_shell.py`'s "no other theme" test reads the palette's results: `get_system_commands` no longer yields
  Textual's commands, Quit included, so the palette adds Quit itself.

## Review

Read the diff against the decisions: nothing outside the ticket. `uv run pytest`, `ruff`, `mypy`: see the PR.
