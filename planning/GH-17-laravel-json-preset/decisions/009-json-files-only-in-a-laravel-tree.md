# 009: A Laravel tree is its top-level JSON files; its directories are left alone

**Date:** 2026-10-23 (ticket pass, Q3; agreed: "ok", to the recommended option 1)

**Question:** `lang/` often holds `en/*.php` (from `php artisan lang:publish`) and `vendor/` beside `fr.json`; the
scanner prefers locale directories, so it takes `lang/en/` for the source and finds no file in it. What then?

**Decision:** **with Laravel's syntax, the scanner reads only the `lang/<lng>.json` files (the file layout) and
ignores the subdirectories.**

- **Why:** the PHP locales are out of scope; without this, most published Laravel projects would scan as a source
  with no files.
- **Not chosen:** the scanner unchanged (the person names `lang/fr.json` by hand, and even then keys as the source
  must come from the siblings).
