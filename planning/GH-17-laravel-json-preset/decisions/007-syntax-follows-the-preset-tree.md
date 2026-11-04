# 007: Laravel's syntax applies to the preset's own locales only

**Date:** 2026-10-23 (ticket pass, Q1; agreed: "ok", to the recommended option 1)

**Supersedes 003** in part: when Laravel's syntax applies.

**Question:** in a Laravel project, which trees do `:name` placeholders, pipe plurals and the keys as the source
apply to?

**Decision:** **the preset's own locales' directory (`lang/`, `resources/lang`), or any tree when `--preset laravel`
is given.** The preset is still detected on every run, a path given or not, and its line is shown (as 003 said); a
path elsewhere in the project keeps today's rules.

- **Why:** many Laravel apps also hold a frontend library's locales (Inertia with vue-i18n or i18next, under
  `resources/js/locales`); vue-i18n uses pipes for plurals in its own way, and its files would be checked with
  Laravel's rules.
- **Not chosen:** whenever Laravel is detected, as 003 had it (wrong rejections in a frontend tree); only with
  `--preset laravel` (the person would have to know the flag, which 003 ruled out).
