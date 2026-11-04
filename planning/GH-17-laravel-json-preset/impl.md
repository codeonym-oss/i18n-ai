# GH-17: implementation plan

Planned against `bf3b3b9` (2026-10-23). Baseline: 281 tests pass on a clean checkout. In the working tree 4 fail
because of the untracked `examples/i18next/locales/ar/` (a manual run's output, not part of this ticket). Run the
suite without it.

Decisions: 001, 002 (in part superseded by 010), 003 (in part superseded by 007), 004–014.

## Read first

- `src/i18n_ai/domain/sub_domains/locale/presets/table.py`, `preset.py`: the preset rows.
- `src/i18n_ai/application/intents/locale/queries/detect_preset/handler.py`, `view.py`: `view()`, `PresetView`.
- `src/i18n_ai/cli/common/presets.py`: `with_preset` (detection only without a path or with `--preset`, today),
  `project_tree`. Callers: `cli/handlers/scan.py`, `cli/handlers/generate.py` (the three branches of step 0).
- `src/i18n_ai/application/ports/locale/scanner.py`: `TreeRequest`.
- `src/i18n_ai/domain/sub_domains/locale/entities/tree.py`: `LocaleTree`, `SourceFile`, `source_path`.
- `src/i18n_ai/infra/adapters/filesystem/tree_scanner.py`: `_from_file`, `_from_directory` (locale directories win
  over locale files), `_file_layout`, `_choose_source`, `_named`.
- `src/i18n_ai/domain/sub_domains/locale/placeholders/tokens.py` (`PlaceholderStyle`, `_FLAT`, `flat_tokens`,
  `styles_in`), `signature.py` (`Signature`, `signature_of`, `detect_styles`).
- `src/i18n_ai/domain/sub_domains/locale/schema/extraction.py`: `LocaleSchema`, `extract_schema`, `_Builder.slot`.
- `src/i18n_ai/domain/sub_domains/locale/rules/translation.py`: `check`, `ViolationCode`, the `_COUNT` exemption.
- `src/i18n_ai/application/intents/locale/queries/scan_locale_tree/handler.py` and
  `commands/generate_locales/handler.py`: both call `extract_schema`, through `EngineRequest` for generation.
- `src/i18n_ai/application/ports/locale/engine.py` (`EngineRequest`), `infra/adapters/langgraph/graph.py:74` (the
  atom's input), `atom.py: extract`, `prompts.py` (`_STYLES`, `translate_system`, `translate_human`).
- `src/i18n_ai/infra/adapters/filesystem/formats/json_format.py: write`: copies the style of `like.path`.
- `src/i18n_ai/cli/rendering/scan.py:40`: the source line of the scan.
- Laravel's `Illuminate/Translation/MessageSelector.php` (`choose`, `extract`, `stripConditions`,
  `getPluralIndex`), MIT: the table to copy, with its notice.
- Tests: `tests/infra/test_presets.py`, `test_tree_scanner.py`, `test_prompts.py`; `tests/domain/test_placeholders.py`,
  `test_rules.py`, `test_schema.py`; `tests/integration/test_generate.py`; `tests/cli/test_cli.py`.
- Docs: `docs/guide/frameworks.md` (its "Placeholders" section says presets are documentation only, which this
  ticket makes untrue for Laravel), `docs/guide/rules.md`, `CONTEXT.md`.

## Steps

Commits follow decision 005: **A** the preset and the scanner (1–5), **B** `:name` (6–8), **C** pipe plurals
(9–12), **D** docs (13).

### A. The preset, the syntax's path, the scanner

1. **`MessageSyntax`**: `domain/sub_domains/locale/vo/syntax.py`, a `StrEnum` with `STANDARD = "standard"` and
   `LARAVEL = "laravel"`, exported through `vo/__init__`, the locale `__init__` and `domain/exports/locale.py`. Add
   `Preset.syntax: MessageSyntax = MessageSyntax.STANDARD` and `PresetView.syntax: str`, filled by `view()`. Add the
   member `PlaceholderStyle.LARAVEL = "laravel"` now (its pattern comes in step 6), so the row can list it.
   → check: `uv run pyright` (or the project's type check) and `pytest tests/infra/test_presets.py` stay green.

2. **The Laravel row**, first in `PRESETS` (decision 013): `name="laravel"`, `library="Laravel"`,
   `example="lang/<lng>.json"`, `packages=("laravel/framework",)`, `trees=("lang", "resources/lang")`,
   `format=JSON`, `placeholders=(Style.LARAVEL,)`, `syntax=MessageSyntax.LARAVEL`. Add `examples/laravel/`:
   `composer.json` (`require: {"laravel/framework": "^11.0"}`), `lang/fr.json` (a few keys: `:name`, `:Name`, one
   `apple|apples`, one `{0} …|[1,*] …`, one `Dashboard | Acme`), and `lang/en/auth.php`.
   → check: `test_each_example_reveals_its_library` has a `laravel` case (`laravel/framework in composer.json`,
   tree `lang`) and passes; a new test shows an app with `laravel/framework` and `vue-i18n` (a `lang/` and a
   `resources/js/locales/`) detects `laravel`; `test_the_table_is_sound` still passes.

3. **The syntax on the request, applied where the preset applies** (decisions 003, 007, 008). Add
   `TreeRequest.syntax: MessageSyntax = STANDARD`. In `with_preset`, always send `DetectPresetQuery` (drop the
   early return for a given path) and always print `describe(match)`. Apply the preset (its `preferred` format and
   its `syntax`) when `named` is set, or when no path is given, or when the given path resolves to `match.tree` or
   inside it. Apply its tree only when no path is given, as today. In `generate.py`'s wizard branch the existing
   `picked == preset_tree.path` test already keeps or drops the preset's request. Nothing else changes for the
   other presets: their syntax is `STANDARD`.
   → check: CLI tests. `i18n-ai scan lang` in the Laravel example prints the preset line, and the request has
   `LARAVEL`. `scan resources/js/locales` in a Laravel project prints the line and keeps `STANDARD`. An i18next
   example scanned with a path now prints its preset line, and its result is otherwise unchanged (update the
   tests that assert no line).

4. **`LocaleTree.syntax` and `source_from`**: `syntax: MessageSyntax = STANDARD`, set by the scanner from the request
   in every layout. `source_from: tuple[str, ...] = ()` is the files a keys' source was built from. `ScanReport`
   gains `source_from`. `render_scan` shows `en English (the keys of de.json, fr.json)` in place of the path when
   it is set (decision 014).
   → check: `test_tree_scanner.py`: a standard tree has `STANDARD` and an empty `source_from`.

5. **The Laravel scan** (decisions 001, 009, 014), in `tree_scanner.py`, used when `request.syntax == LARAVEL`:
   - A directory: look only at its top-level `*.json` files whose stem is a locale (`_locale_of`), and ignore its
     subdirectories. A file path (`lang/fr.json`) is scanned as its directory.
   - The source is `request.source` or `en`. When `<source>.json` exists, take the file layout as `_file_layout`
     does, with the other locale files as `existing`.
   - Otherwise, build the keys' source. Read every locale file in name order (`load_document`). The keys are taken
     in order of first appearance, for every key whose value is a string. The document is `{key: key}`. The
     `SourceFile` has `name=PurePosixPath(f"{source}.json")` and `path=` the first locale file, so that
     `JsonFormat.write` copies that file's style (decision 014). Say this in `SourceFile`'s docstring. Set
     `source_from=` the file names, `existing=` every locale file, and `layout=FILE`, `prefix=""`, `format=JSON`.
   - No locale file at all: `LocaleTreeNotFound` as today.
   → check: new tests in `test_tree_scanner.py`:
     - `fr.json` and `de.json` with no `en.json`: the source is `en`, the keys are the union in order, and both
       files are `existing`.
     - With an `en.json`: it is the source.
     - With `lang/en/auth.php` beside them: still the file layout.
     - `--source fr` with `fr.json`: `fr.json` is the source.
     - The same directory without `LARAVEL` behaves as today (`SourceLocaleUnknown` for `fr` and `de`).
     - The target `de.json` is written with `fr.json`'s indent.

### B. `:name` placeholders

6. **The style** (decision 004): `PlaceholderStyle.LARAVEL`'s pattern,
   `(?<!\w):[A-Za-z_]\w*`. It is not part of `_FLAT`. `flat_tokens`, `styles_in`, `signature_of` and
   `detect_styles` take `syntax: MessageSyntax = STANDARD` and look for it only with `LARAVEL`. A token is
   normalized to lower case (`:Name` → `:name`), so counts compare names, not case.
   → check: `test_placeholders.py`:
     - `Welcome, :name!` has the token `:name` with `LARAVEL` and none with `STANDARD`.
     - `:Name` and `:NAME` give `:name`.
     - `Ratio:high`, `10:30` and `mailto:me` give no token.
     - `:name and :name` gives two.

7. **The schema carries the syntax**: `extract_schema(document, source, target, syntax=STANDARD)`, and
   `LocaleSchema.syntax`. `_Builder.slot` and `detect_styles` use it, and `check` passes `schema.syntax` to
   `signature_of`. The callers pass `tree.syntax`: the scan handler directly, and the generation through
   `EngineRequest.syntax` → `graph.py` (into the atom's state, next to `source`) → `atom.extract`.
   → check: `test_rules.py`:
     - In a `LARAVEL` schema, a lost, added or renamed `:name` is rejected (`placeholders`), and `:name` → `:Name`
       passes.
     - In a `STANDARD` schema, `Ratio:high` → `Ratio:hoch` passes.
     - The integration test for i18next is unchanged.

8. **The prompt**: a `_STYLES[LARAVEL]` entry, ``"`:name` placeholders"``, and with the style a rule saying "`:name`
   renders the value as given, `:Name` capitalized, `:NAME` in capitals: keep the name, change the case only where
   the grammar needs it".
   → check: `test_prompts.py` asserts the rule appears for a `LARAVEL` schema and not otherwise.

### C. Pipe plurals

9. **Laravel's plural table**: `domain/sub_domains/locale/plurals/laravel.py` (or beside `vo/locale_code.py`; match
   whichever the code reads better from). It holds `getPluralIndex` copied as data: the language lists of each rule
   and the rule functions, with Laravel's MIT notice. A language not in the table gets index 0, as in Laravel. It
   offers `laravel_form_count(locale) -> int` and `laravel_form_counts(locale) -> tuple[str, ...]`, the counts that
   reach each index, read over 0…200 like `plural_forms._SAMPLES` (`"1, 21, 31, …"`). Look up the full locale key
   first, then the language.
   → check: unit tests: `ru` gives 3, `ja` 1, `fr` 2, `ar` 6, `en` 2; an unknown language gives 1; `fr`'s first
   form serves 0 and 1.

10. **Parsing** (decisions 002, 010): `parse_pipes(text) -> PipePlural | None`. A form is `(range, text)`. `range` is
    `{n}`, `[a,b]` or `[a,*]` as written, else None; the regex is Laravel's `extractFromString`'s. A message is a
    pipe plural when one of its forms has a range, or one of its `|` has no space on both sides. The signature
    gains `pipes: PipePlural | None`. `signature_of` computes the tokens over the forms' texts with the ranges
    removed, so `{0}` is not taken for an ICU argument.
    → check: `test_placeholders.py`:
      - `apple|apples` and `{0} none|[1,*] some` are pipe plurals.
      - `Dashboard | Acme` and `a | b | c` are not.
      - `one | [2,*] many` is one (it has a range).
      - `{0} :count none` has the token `:count` and no `{0}`.
      - With `STANDARD`, nothing is parsed.

11. **The rules** (decisions 011, 012): in `check`, when `unit.signature.pipes` is set:
    - **The forms:** with no range in the source, the translation has `laravel_form_count(target)` forms, else
      `pipe-forms`. With ranges only, it has the same ranges in the same order, else `pipe-ranges`. With both kinds
      (rare), it keeps the source's shape: the same number of forms and the same ranges at the same places.
    - **The placeholders:** compared as sets of the source's and the translation's tokens (normalized), in place of
      the counts. Missing and unexpected are reported as today.
    - A translation of a pipe plural that is not one (one form with no range) is reported as `pipe-forms`.
    The two new `ViolationCode`s are errors.
    → check: `test_rules.py`:
      - Into `ru`: `:count apple|:count apples` → 3 forms passes, 2 forms is rejected.
      - Into `ja`: 1 form passes.
      - Into `fr`: 2 forms pass.
      - `{0} none|[1,*] some`: a changed `[1,*]` is rejected, and so is a missing form.
      - `:name` in only one of three forms passes; a new `:city` is rejected.
      - `Dashboard | Acme` → `Tableau de bord | Acme` passes as plain text.

12. **The prompt** (decision 011): in `translate_human`, a pipe-plural unit gets
    `"pipe_forms": ["1, 21, 31, …", "2–4, 22–24, …", "0, 5–20, …"]` for its unranged forms, the counts from step 9,
    and `"keep_ranges": ["{0}", "[1,*]"]` for its ranged ones. In `translate_system`, when a unit has pipes, add a
    rule: "write a pipe plural as its forms separated by `|`, with no space around it: as many forms as
    `pipe_forms` lists, each for those counts, and keep each range written before its form".
    → check: `test_prompts.py` asserts the fields for `ru` and `ja`. In the integration test (step 13) the
    `FakeGateway` answers with the expected shapes.

### D. End to end, and the docs

13. **Integration and docs.**
    - `tests/integration/test_generate.py`: the Laravel example, scanned with `LARAVEL` and no `en.json`, generates
      `de.json` with every key of `fr.json`, translated from the key. A second case adds an `en.json`, which becomes
      the source. A third goes into `ru` with the right number of forms.
    - `tests/cli/test_cli.py`: `i18n-ai scan` with no path in the example shows `Preset laravel` and
      `the keys of fr.json`.
    - `docs/guide/frameworks.md`: a "Laravel" section (found by, locales, format, placeholders `:name`, pipe
      plurals, the keys as the source, PHP files left alone, frontend trees keep their rules). Correct the
      "Placeholders" section: Laravel's syntax is the one case where a preset turns rules on.
    - `docs/guide/rules.md`: `pipe-forms`, `pipe-ranges`, and the set comparison.
    - `CONTEXT.md`: **Pipe plural** and **Message syntax** in the glossary.
    → check: the full suite (`uv run pytest`) passes, with coverage at or above 85%. `uv run ruff check` and the
    type check are clean. A manual `i18n-ai generate --dry-run -t de` in `examples/laravel` shows the plan.

## Tests

- **Domain** (`tests/domain/`): the `:name` token and its case, `parse_pipes`, Laravel's form counts, `check` for
  each new violation. This is the main seam: pure functions on strings.
- **Infra** (`tests/infra/`): preset detection and order, the Laravel scan (keys' source, `en.json`, PHP
  directories, target style), and the prompts.
- **Application and integration**: `ScanLocaleTreeQuery` and `GenerateLocalesCommand` on `examples/laravel` with
  the fake gateway.
- **CLI**: the preset line shown on every run, and Laravel's syntax applied to `lang/` but not to another path.

## Risks

- **The preset line is now shown on every run, path given or not** (decision 003). CLI tests that compare output
  will change. Only Laravel's syntax depends on the path; for every other preset only the printed line and the
  applied format are new. Check: the whole CLI suite passes, and the changed assertions only add the line.
- **The preferred format with a path inside the preset's tree**: a mixed-format tree inside a preset's directory now
  reads the preset's format instead of raising `MixedLocaleFormats`. This is intended (decision 007, "the whole
  preset applies where its syntax does"). Check: one test for it.
- **The keys' source points at another locale's file** (`SourceFile.path` is `fr.json`). Code that treats
  `source_path` as the source file (`render_scan`, an ignored file's `FileResult.path`) must use `source_from`.
  Check: grep for `source_path` and `.path` on source files in `cli/rendering` and the handlers.
- **`signature_of` gains a parameter.** Each caller passes it or keeps the default. A forgotten caller would
  silently check Laravel messages with the standard rules. Check: grep for `signature_of(` and `extract_schema(`
  and make sure every call in a Laravel path passes the syntax.
- **ICU braces in Laravel files**: Laravel does not use ICU, but `{…}` is still parsed as ICU (as today). Only
  ranges are stripped first. A Laravel message with stray braces gets today's behaviour. That is left as is, not
  widened.
- **Copied Laravel code**: keep the MIT notice with the table.

## Corrections made while building

- **Step 6:** the `:name` pattern is `(?<![A-Za-z0-9_]):[A-Za-z_][A-Za-z0-9_]*`, ASCII on both sides. With `\w`,
  Japanese `りんご:count個` found no placeholder (the lookbehind) or found `:count個` (the name).
- **Step 9:** the table is kept by language. Every region in Laravel's table shares its language's rule (checked
  against `MessageSelector.php`). The rules were verified against Laravel's PHP expressions for 0…10,000. Their
  notice is Zend's BSD one, which Laravel's comment carries, as well as Laravel's MIT.
- **Step 10:** a range counts only at the very start of a form, as Laravel's regex reads it, so `one | [2,*] many`
  is text, not a plural.
- **Step 12:** `translate_human` takes the target as a required argument, so a pipe plural's forms are never left
  out by a caller. The fake gateway answers a pipe plural in the target's shape from step 11 on.
