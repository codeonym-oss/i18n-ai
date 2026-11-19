# GH-72: implementation plan

Planned 2026-11-19 against `main` at c5f2a15. Ticket decisions 001–005; story decisions 001–006 (one look in
`aurora.tcss` and `kit/`, breakpoints, snapshots at 160×45 and 80×24, nothing new underneath); #15 decisions 002
(the review writes, checked) and 008 (what the record keeps).

## Read first

- `src/i18n_ai/cli/tui/review.py`: `ReviewScreen` (list, `_detail`, mark, retry, accept, back) and `EditScreen`.
- `src/i18n_ai/application/intents/locale/queries/list_fallbacks/`: `handler.py`, `view.py` (`FallbackView`).
- `src/i18n_ai/application/common/fallbacks.py`: `record_targets`.
- `src/i18n_ai/application/intents/locale/commands/generate_locales/handler.py` ≈ 113–121: the whole tree scanned in
  the format read.
- `src/i18n_ai/cli/tui/kit/widgets.py` (`Card`, `Chip`), `aurora.tcss`, `app.py` (`open_review`, `leave_review`).
- Tests: `tests/integration/test_review.py`, the review tests in `tests/tui/test_tui.py`,
  `tests/tui/test_snapshots.py`, `tests/support/tui.py` (`fallen`).

## The design, point by point

- **The query** (decisions 004, 005): `FallbackView.elsewhere: tuple[tuple[LocaleCode, str | None], ...]`, the
  same message in each other target locale of the entry's source file, in the tree's order; empty for a stale entry.
  The handler scans the whole tree in the format read when the request filters.
- **The layout** (decision 001): the body is `#review` (a `Horizontal`): `#fallbacks` (the `DataTable`, 40 wide),
  `#focus` (the header, `#cards` with `#source`, `#model`, `#now`, the `#editor` card with `Input#text` and
  `Static#check`, the keys line) and `#elsewhere` (a `Card`, 30 wide). Narrow: a `Vertical`, the list at most 6
  rows, the three cards one under the other at one line each, `#elsewhere` under the editor. `#empty` and `#hint`
  as today.
- **The header:** `<locale> · <file> · <key>`, a `Chip` of the first rule (warning tone), `1 of 5 · 2 marked`
  and `· 1 stale` when there are.
- **The editor** (decisions 001, 002): `Input#text` holds the current text; `tab`/`e` focus it; `enter` sends
  `SetMessageCommand`; refused: `#check` shows the violations (error tone), the text kept; written: the list reloads
  and the cursor stays at its row (the next fallback). `escape` in the editor gives the focus back to the list;
  elsewhere it goes back as today. A stale entry: the editor disabled.
- **Unchanged:** the commands, mark/retry/accept and their bindings, `open_review`, `leave_review`, the sidebar count.

## Steps

1. **`elsewhere` in the view; the scan keeps the format.** → check: `tests/integration/test_review.py`: a fallback
   in `it` lists `fr`'s text and a missing `de` (None); a stale entry has none; a mixed tree with `*.yml` excluded
   lists its fallbacks.
2. **The screen's layout and header.** `#review`, the three cards, the header, `#elsewhere`; `EditScreen` goes.
   → check: the TUI review tests: the header, the cards' text, the elsewhere panel.
3. **The editor.** `tab`/`e` into it, `enter` saves, refused shows the violations, `escape` back to the list.
   → check: the moved tests (`tests/tui/test_review_screen.py`): an edit is checked then written; a run that leaves a
   fallback opens its review and an edit fixes it; escape leaves the editor, then the screen.
4. **Retry, accept, stale carried over.** → check: the moved tests pass.
5. **Snapshots** at 160×45 and 80×24 (`test_review`). → check: they look as the design, nothing cut at 80×24.
6. **Docs:** `docs/guide` where the review is described. → check: `uv run mkdocs build --strict` if docs change.

## Risks

- `escape` is the screen's Back: the editor must take it first.
- The 80×24 layout: the cards, editor and panel must fit under a six-row list.

## Corrections while building

- The review's rules are in `aurora.tcss` ("The review screen"), not the screen's `DEFAULT_CSS`: the app's sheet
  wins over a default one whatever its specificity, so the narrow rules for `.card` did not apply (story decision
  003 wants them there anyway).
- The cards are titled `Source`, `Last attempt` and `In the file` (`SOURCE`, `MODEL`, `NOW` when narrow): at
  160×45 `Model · last attempt` and `In the file now` were cut by their cards' width (decisions 001, 003 name them
  so).
- The list drops its `Current` column: the text now is in its card, and the list is 46 columns wide.
- `tab` needs no binding: it moves from the list to the editor as the next focus.
- The TUI tests are in `tests/tui/test_review_screen.py`: `test_review.py` is the integration tests' name, and
  pytest refuses two modules of one name.
- The query's view tests: `fr`'s text beside an `it` fallback, `None` once `fr` lacks the message, none for a stale
  entry, and a mixed tree with `*.yml` excluded (the follow-up's test).

## Review

Read the diff against the decisions: nothing outside the ticket; the follow-up `review-scan-loses-the-format` is
fixed and can be closed with it. `uv run pytest`: 494 passed, 18 snapshots; `ruff`, `mypy` clean.
