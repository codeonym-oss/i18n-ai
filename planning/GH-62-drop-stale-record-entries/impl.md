# Implementation: drop the fallback record's entries whose target is gone

Written 2026-11-10 against `main` at 27a95d1. Rests on GH-29's decisions 002–003 and GH-33's 007 (in
`planning/GH-15-full-screen-tui/`), and this ticket's 001–005.

## Read first

- `src/i18n_ai/application/intents/locale/commands/generate_locales/handler.py`: step 2's scan, step 3's
  `recorded`, and the `finally` that writes the record only `if written`.
- `src/i18n_ai/application/intents/locale/queries/list_fallbacks/handler.py`: step 1, the mapping that moves, and
  its `_Place` alias.
- `src/i18n_ai/application/common/fallbacks.py` (`record_target`) and `common/__init__.py`.
- `src/i18n_ai/application/ports/locale/fallbacks.py`: `RecordedFallback` (frozen, `.target`), `IFallbackRecord`.
- `src/i18n_ai/infra/adapters/filesystem/fallback_record.py`: `write` sorts and rewrites, and unlinks when empty.
- `tests/integration/test_generate.py`: `generate(...)`, `Stubborn`, `Unreachable`, the record tests from line 431;
  `tests/integration/test_review.py`.
- `docs/guide/rules.md`, "When a message never passes".

## Steps

1. **The mapping, shared** (decision 004). `common/fallbacks.py`: `record_targets(tree: LocaleTree) ->
   dict[place, tuple[SourceFile, LocaleCode, TargetLocation]]`, the review's step 1 as it is (every qualifying
   source file × every locale in `tree.existing` but the source); exported from `common`. `ListFallbacksQueryHandler`
   calls it in place of its loop.
   → check: `tests/integration/test_review.py` passes unchanged.

2. **`generate` drops the entries with no target** (decisions 001, 002). In the handler, after step 3's `read`:
   the mapping of `tree`, or of a second scan with `replace(command.tree, include=(), exclude=())` when the command
   has either (decision 004). In the `finally`: `kept` = the recorded entries that have a target in the mapping and
   whose target was not written; the record is `kept + entries`, and written only when it differs from `recorded`
   (compared regardless of order), so an unchanged record is not touched and an empty one is removed by `write` as
   today.
   → check, new tests in `test_generate.py`, each red first:
   - a removed source file: record `it/common.json` and `it/gone.json` (Stubborn on a copied `gone.json`), delete
     `en/gone.json`, run `common.json` again with `FakeGateway`: no record left;
   - a removed locale: Stubborn into `it` and `de`, remove `de/`, run `it`: only `it`'s entries stay;
   - a run that writes nothing: as the first, the second run `Unreachable`: the `gone.json` entries are gone;
   - kept: Stubborn into `it` with `gone.json` and `common.json`, run `de` with `exclude=("gone.json",)`: `it`'s
     entries all stay (a locale outside the run, an excluded file);
   - untouched: a record whose entries all have targets, a run of another locale with no fallbacks: the file's
     bytes and `stat().st_mtime_ns` are the same.
   The existing record tests pass, `test_a_refused_or_failed_file_leaves_the_record_as_it_was` among them.

3. **The log line** (decision 003). `logger.info("dropped %d fallback record entries with no target: %s", n,
   ", ".join(sorted target files))` in the handler, only when some were dropped.
   → check: a `caplog` test at INFO on the removed-file case reads "dropped 1 fallback record entries with no
   target: it/gone.json"; nothing logged when none are dropped.

4. **Docs.** `docs/guide/rules.md`: one sentence after "takes it off the record once it passes": a message whose
   file or locale is gone leaves the record on the next run too.
   → check: `uv run --frozen sphinx-build -W --keep-going -b dirhtml docs docs/_build/html`.

5. **Everything.** `uv run --frozen ruff check . && uv run --frozen ruff format --check .`, `uv run --frozen mypy`,
   `uv run --frozen lint-imports`, `uv run --frozen pytest` (coverage ≥ 85 %).

## Tests

- **Integration** (`tests/integration/test_generate.py`): the five record cases of step 2 and the log line of step 3,
  through the container with the fake gateway.
- **Integration** (`tests/integration/test_review.py`): unchanged, for the move of step 1.

## Risks

- **The filtered scan:** without the second scan, an excluded file's entries would be dropped; the `exclude` test of
  step 2 covers it, and every existing record test runs with `include=("common.json",)`.
- **An interrupted run** reaches the `finally` too: it drops the entries with no target, which is what a finished
  run does, so nothing is lost.
- **A mixed-format tree** read in one format drops the other format's entries (decision 005), as the review already
  calls them stale.
- **Test fixtures:** the copied example tree is per test (`examples` fixture); a removed file or locale must be
  removed in that copy, never in `examples/`.

## Corrections while building (2026-11-10)

- **The second scan keeps the format read** (`format=tree.format`): in a directory layout the scanner picks the
  format after `--include` and `--exclude`, so `--exclude '*.yml'` can be what leaves a mixed tree with one format;
  scanned without it, the tree raised `MixedLocaleFormats` where the run worked before. Test:
  `test_a_mixed_tree_with_a_format_excluded_is_still_generated`. Decision 005 stands: the mapping covers the format
  read.
- **The `exclude` test is a guard,** not red first: on `main` a run of another locale already leaves the entries; it
  fails if the mapping is built from the filtered tree.
