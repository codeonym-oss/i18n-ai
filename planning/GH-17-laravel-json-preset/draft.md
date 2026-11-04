# Translate Laravel's JSON locales, keeping their :name placeholders

## Problem

i18n-ai presets 13 i18n libraries (#24), but not Laravel. A Laravel project's JSON locales differ from the others in
three ways that i18n-ai does not handle yet:

- **The keys are the English text.** `lang/fr.json` holds `{"Welcome, :name!": "Bienvenue, :name !"}`, and most
  projects have no `lang/en.json`: the English lives in the PHP code. i18n-ai would take `fr` for the source.
- **Placeholders are `:name`**, capitalized as `:Name` or `:NAME` to render the value so. Nothing checks them, so a
  lost or renamed one goes through.
- **Plurals are pipes**, read by `trans_choice`: `one apple|many apples`, or with ranges,
  `{0} none|[1,19] some|[20,*] many`. A translation with the wrong number of forms makes Laravel pick a form that
  does not exist.

## The fix

- **A Laravel preset**, found from `laravel/framework` in `composer.json`, first in the table (decision 013), its
  locales in `lang/` (or `resources/lang` before Laravel 9), in JSON. Only the top-level `lang/<lng>.json` files are
  read; `lang/en/*.php` and `lang/vendor/` are left alone (decision 009).
- **The keys as the source** (decisions 001, 014): `lang/en.json` when it exists; otherwise the keys of the existing
  locale files, all together, in the order they first appear, are the English source, each key's text being the
  key. The scan says so: `en (the keys of de.json, fr.json)`. `--source` names another language.
- **`:name` placeholders** (decision 004): a placeholder style of their own. A translation keeps each one, as often
  as it appears; its case may change (`:name` → `:Name`), its name may not. The model is told what each case renders.
- **Pipe plurals** (decisions 002, 010, 011, 012): a message with a range or an unspaced `|` is one; ` | ` with
  spaces and no range is text (`Dashboard | Acme`). Forms without a range get the target language's number of forms,
  from Laravel's own plural table (not CLDR's: Laravel gives French 2 forms), each described to the model by the
  counts it serves. Forms with a range keep it as written. The rules check the number of forms and the ranges; the
  placeholders are compared over the whole message, as a set.
- **In Laravel's own locales only** (decisions 003, 007, 008): `:name` and pipes are ordinary text elsewhere, so
  Laravel's syntax applies to the preset's directory, or to any tree with `--preset laravel`. The project's preset
  is detected and shown on every run, a path given or not; a path elsewhere in a Laravel project (an Inertia app's
  `resources/js/locales`) keeps today's rules.
- One pull request (decision 005), its commits keeping the scanner, the rules and the plurals apart.

## Out of scope

- Laravel's PHP locales, `lang/<lng>/*.php`, and `lang/vendor/`.
- Extracting the strings found only in the PHP code (`__()`, `trans()`, `@lang`): a key no locale file has yet is not
  translated.

## Done when

- A Laravel fixture project (`composer.json`, `lang/fr.json`, `lang/en/auth.php`, no `en.json`) is detected,
  scanned with no path, and generated: `lang/de.json` gets every key of `fr.json`, translated from the key's English.
- With a `lang/en.json`, it is the source.
- A lost, added or renamed `:name` is rejected; `:name` → `:Name` passes; in an i18next project, and in a vue-i18n
  tree of a Laravel project, `Ratio:high` is not a placeholder.
- `apple|apples` into Russian needs 3 forms and into Japanese 1; into French 2. `{0} none|[1,*] some` keeps its ranges
  in every language; a missing form or a changed range is rejected. `Dashboard | Acme` is translated as text.
- `i18n-ai scan lang` in a Laravel project shows the Laravel preset and checks `:name`.
- The "Your framework" page has a Laravel section.
