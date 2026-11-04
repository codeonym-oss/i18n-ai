# GH-33 implementation plan: review the fallbacks in the TUI

Planned 2026-11-04 against `main` at 798608c (383 tests passing, 94% coverage). Decisions: story GH-15 002, 003,
007, 008, 009, 010; this ticket's 001–007. Two pull requests (decision 004): **PR 1** is steps 1–7, **PR 2** is
steps 8–13.

## Read first

- `src/i18n_ai/application/intents/locale/commands/generate_locales/handler.py`: how a run builds the
  `EngineRequest`, strips recorded fallbacks from `existing`, writes each `FileTranslated` and rewrites the record
  (`_recorded`, the `finally` block).
- `src/i18n_ai/application/intents/locale/queries/scan_locale_tree/handler.py`: the pattern a query over the tree
  and the record follows (scan, qualify, `target_location`, `record_target`).
- `src/i18n_ai/application/common/fallbacks.py`: `record_target`, `recorded_paths`.
- `src/i18n_ai/application/ports/locale/fallbacks.py`, `engine.py`, `store.py`: `RecordedFallback`,
  `IFallbackRecord`, `EngineRequest`, `FileTranslated`, `ILocaleStore`.
- `src/i18n_ai/infra/adapters/filesystem/fallback_record.py`: the record's file.
- `src/i18n_ai/domain/sub_domains/locale/entities/document.py` (`LocaleDocument.get`, `without`),
  `schema/extraction.py` (`extract_schema`, `SourceUnit`; a unit's `path` is the **target's**, so a plural form's
  source text comes from the unit, not the source document), `rules/translation.py` (`normalize`, `check`,
  `errors`), `exceptions/tree.py` (the exception style).
- `src/i18n_ai/infra/adapters/langgraph/atom.py` `extract`: why an unchosen fallback is reused (its source text
  passes `check`) and a chosen one, removed from `existing`, is translated.
- `src/i18n_ai/cli/tui/app.py`, `setup.py` (`_scan`, `_run`, `action_plan`), `run.py` (`show_receipt`,
  `check_action`), `plan.py` (`space` toggling, `JobGrid` in `grid.py`).
- Tests: `tests/integration/test_generate.py` (`generate`, `Stubborn`, the record tests from line 431),
  `tests/support/fakes.py` (`FakeGateway(broken_first=...)`, `FakeModel`), `tests/tui/test_tui.py` (`tui`,
  `settle`, `ready`, `ended`, `cells`).

## Shapes

Shared by the three commands and the query (in `application/ports/locale/fallbacks.py`, beside `RecordedFallback`):

```python
@dataclass(frozen=True)
class MessageRef:
    """A message of a target: its source file, the target, and its path there."""

    file: PurePosixPath
    target: LocaleCode
    path: KeyPath
```

## Corrections while building

- **Step 1:** `with_value` makes a missing object on the way (a hand-edited target can lack one) and raises
  `ValueError` when the path cannot hold a value; an array's item must be there.
- **Step 3:** `FallbackView` holds the `entry: RecordedFallback` itself (its file, key, path, problems and rejected
  text), then `ref`, `source`, `current` and a `stale` property: accept takes the entries back as they are.
- **Steps 4, 6, 7:** set-message, retry and accept scan without `include`/`exclude` as well, for the reason of
  step 3.
- **Steps 5, 6:** `_settle` moved to `application/common/settle.py` as `settle` (with `WRITTEN`) beside
  `recorded_fallbacks`: retry writes the same way, and honours `options.strict` at no cost.
- **Step 6:** for each target it writes, retry drops the chosen entries **and every path the event reports**, then
  adds all of the event's fallbacks, not the chosen ones only: a message never translated before (decision 001's
  accepted edge) that falls back is recorded too. The unchosen fallbacks are reused, so the event does not report
  them, and they stay.

## Steps

### PR 1: the intents (`Part of #33`)

1. **`LocaleDocument.with_value(path, text)`** in `domain/.../entities/document.py`: a copy with `text` at `path`,
   which must already lead to an object or array slot (the target was written by a run); returns a new document,
   like `without`.
   → check: `tests/domain/test_document.py`: a nested key, an array item, and a plural key (`item_few`) are set,
   the original is unchanged.

2. **Domain exceptions** in `domain/.../exceptions/tree.py`, exported like the others: `MessageUnknown(file,
   target, path)` (the path is no message of the source's schema for that target, decisions 003, 007) and
   `TargetNotGenerated(file, target)` (set-message on a target that has no document yet: there is nothing to fix).
   → check: `uv run pytest tests/domain -q`; they appear in `domain.exports.locale`.

3. **`ListFallbacksQuery(tree: TreeRequest) → FallbacksView`** in `application/intents/locale/queries/list_fallbacks/`
   (`query.py`, `view.py`, `handler.py`, `__init__.py`), exported from `intents/locale/__init__.py`. The handler
   scans the tree **without `include`/`exclude`** (an excluded file's fallbacks are still fallbacks), reads the
   record at `tree.target_directory`, and maps each qualified source file × each of `tree.existing` (but the
   source) to its `record_target` place. Each entry becomes a `FallbackView`: `ref: MessageRef | None`, the target
   file shown, `path`, `source` (the schema unit's `source`, None when stale), `current` (the target's value),
   `problems`, `rejected`. An entry whose place, or path in that schema, is not found is stale: `ref` and `source`
   None (decision 007). `FallbacksView.entries` keeps the record's order.
   → check: `tests/integration/test_review.py` (new): after a `Stubborn` run (as in `test_generate.py`), the query
   gives one entry with the source `Welcome back, {{name}}!`, the rejected text and `placeholders`; after the
   source key is deleted from `en/common.json`, the same entry comes back stale.

4. **`SetMessageCommand(tree, message: MessageRef, text) → MessageSet`** in
   `commands/set_message/`. The handler scans, finds the source file (`MessageUnknown` if none), the target's
   location and document (`TargetNotGenerated` if none), builds the schema, finds the unit whose `path` is
   `message.path` (`MessageUnknown` if none), then `normalize` + `check`. With an error: returns
   `MessageSet(written=False, violations=...)` and writes nothing. Otherwise writes
   `document.with_value(path, text).content` through `ILocaleStore.write(location, …, like=file)`, removes the
   `(place, path)` entry from the record if it is there (writing the record only then), and returns
   `MessageSet(written=True, violations=<warnings>)`. A refused text is a result, not an exception: it is an
   expected outcome the screen shows.
   → check: in `test_review.py`: a passing edit is written and leaves the record; a text missing `{{name}}` is
   refused, and the file and the record are byte-for-byte unchanged; an unrecorded message is set and the record is
   untouched; an unknown path raises `MessageUnknown`.

5. **Move `_recorded`** from the generate handler to `application/common/fallbacks.py` as
   `recorded_fallbacks(place, event)` (its second user is step 6); the generate handler calls it.
   → check: `uv run pytest tests/integration -q` unchanged.

6. **`RetryFallbacksCommand(tree, model: ModelSpec, messages: tuple[MessageRef, ...], options: GenerationOptions)
   → GenerationReceipt`** in `commands/retry_fallbacks/` (decision 001). The handler resolves the model (and
   `ProviderNotInstalled`) as generate does; scans; groups `messages` by (file, target), leaving out those whose
   file is not in the tree; for each group reads the target document and gives the engine
   `existing[(file.name, target.key)] = document.without(<the group's paths>)`, so only the chosen paths (and
   anything never translated) are sent. `EngineRequest(files=<the groups' files>, targets=<their targets>,
   skip=<every other file × target pair>, settings=EngineSettings(…, classify=False))`: the files were classified
   by the run that left the fallbacks. Each `FileTranslated` is written as in
   generate (`_settle` without strict: the TUI has none, story decision 003); the record keeps every entry but
   the chosen ones, plus `recorded_fallbacks(place, event)` **for the chosen paths only** (the unchosen fallbacks
   were reused, so the event does not report them, and they must stay). Progress is not reported (the review shows
   the receipt).
   → check: in `test_review.py`, with two fallbacks in `common.json` (a `Stubborn` that drops `{{name}}` and
   `{{amount, currency(EUR)}}`: `app.welcome` and `cart.total`), retrying one
   with `FakeGateway()`: the gateway's batches hold only that path, it is written and leaves the record, the other
   stays recorded and unchanged on disk; with a gateway that breaks it again, it stays recorded with the new
   rejected text.

7. **`AcceptFallbacksCommand(tree, entries: tuple[RecordedFallback, ...]) → None`** in
   `commands/accept_fallbacks/` (decision 002): reads the record, writes it without those entries (compared by
   `target` and `path`, so a stale entry is accepted too). No locale file is touched.
   → check: in `test_review.py`: accepting one of two leaves the other; accepting the last removes the file;
   the target file's mtime is unchanged.
   → PR 1 check: `uv run pytest -q`, `uv run mypy`, `uv run ruff check`, `uv run lint-imports` pass.

### PR 2: the review screen (`Closes #33`)

8. **`ReviewScreen(mediator, tree: TreeRequest, model: ModelSpec | None)`** in `cli/tui/review.py`: a `DataTable`
   with a mark column, file → locale, key path, rule, current text; a detail `Static` under it with the source, the
   rejected translation and the problems' messages of the highlighted row; a stale row shows "no longer in the
   source". Loaded from `ListFallbacksQuery` on mount and after each action. Bindings: `space` mark, `e` edit,
   `r` retry, `a` accept, `b`/`escape` back (decision 006). Empty: "No fallbacks to review".
   → check: `tests/tui/test_review.py` (new): after a CLI `generate` with `Stubborn` on a copy of
   `examples/i18next`, the screen lists the entry with its source and rule.

9. **Edit**: `e` opens an `EditScreen` (a `ModalScreen[str | None]`, like `confirm.py`) with an `Input` holding the
   current text; on submit, `SetMessageCommand`; refused, the dialog stays open with the violations under the
   input; written, the table reloads. Not on a stale row.
   → check: Pilot test: edit the fallback to `Bentornato, {{name}}!`, find it in `it/common.json` and out of the
   record; a text without `{{name}}` shows `missing {{name}}` and writes nothing.

10. **Retry and accept**: `r` sends `RetryFallbacksCommand` for the marked (or highlighted) non-stale rows in a
    worker, with the form's model; with no model, `r` is off (`check_action`) and the footer says "pick a model in
    the setup to retry" (decision 005). `a` sends `AcceptFallbacksCommand` for the marked (or highlighted) rows,
    stale ones included. Both reload the table.
    → check: Pilot tests: marking two and retrying with `FakeGateway()` leaves none; accepting one leaves the other.

11. **From the run**: `RunScreen` gets `v` Review, shown (`check_action`) when the run is done and the record has
    entries; it pushes `ReviewScreen` with the run's tree request and model. `SetupScreen._run` passes them in.
    → check: Pilot test: a run with `Stubborn` ends, `v` opens the review with the run's fallback.

12. **From the start**: after `SetupScreen._scan`, `ListFallbacksQuery`; with entries, a line under the tree
    ("N fallbacks recorded · v to review") and `v` on; it pushes `ReviewScreen` with the form's tree request and its
    model when one is picked. Both ways in get a palette command in `I18nAiApp.get_system_commands`.
    → check: Pilot test: with a record left by a CLI run, the setup shows the line, `v` opens the review, an edit
    clears it, and back on the setup the line is gone.

13. **Story-level run**: one Pilot test from setup to review on a copy of `examples/i18next` with the fake model:
    fill the form, plan, run with a fallback, review, edit it, and find every target written and no record.
    → check: `uv run pytest -q` (whole suite), `mypy`, `ruff`, `lint-imports`; the story's Done-when boxes for the
    review are met.

## Tests

- **Domain:** `with_value` (`tests/domain/test_document.py`).
- **Intents, through the mediator with the fake model** (`tests/integration/test_review.py`, its own `generate`
  helper as in `test_generate.py`): the query (live and stale), set-message (written, refused, unrecorded, unknown),
  retry (only the chosen paths sent; written and unrecorded; failing again, recorded anew; the others kept), accept
  (one, the last, stale).
- **Screens, through `Pilot`** (`tests/tui/test_review.py`): listing, edit (passing, refused), retry and accept on
  marked rows, retry off without a model, both ways in, and the setup-to-review run.

## Risks

- **The generate handler's behaviour** (step 5 moves `_recorded`): the existing record tests in
  `test_generate.py` pin it; they must pass unchanged.
- **Retry dropping an unchosen fallback from the record:** the event only reports the chosen paths' failures, so
  the record update must keep the unchosen entries explicitly; step 6's two-fallback test covers it.
- **A record written by an older version or by hand:** `FileSystemFallbackRecord.read` already returns none for an
  unreadable record; the screen then shows nothing to review.
- **A query that scans with the form's `include`/`exclude`** would mark an excluded file's fallbacks stale; the
  query clears them (step 3), tested with an include that leaves the file out.
- **`textual` outside `cli/tui`:** `lint-imports` (the contract from #30) fails the build if a step slips.
- **Concurrent edits** (the person edits a locale file by hand while the review is open): each command reads the
  file and the record afresh, and the screen reloads after each action; nothing is cached across actions.
