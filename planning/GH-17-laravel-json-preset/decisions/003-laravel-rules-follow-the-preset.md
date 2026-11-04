# 003: Laravel's placeholders and plurals apply in a Laravel run only

**Superseded by 007** (in part: which trees the syntax applies to).

**Date:** 2026-10-23 (grilling, Q3; agreed: "1")

**Question:** when are `:name` placeholders and pipe plurals checked, given that colons and pipes are ordinary text
in other libraries' messages?

**Decision:** **when the Laravel preset is detected or named.** To that end the project's preset is detected on
every run, a path given or not; its locales' directory is still used only when no path is given. Every other
project's checks stay as they are.

- **Why:** the syntax only means something in Laravel's files, and the preset is what knows a project is Laravel.
- **Changes from #24:** a preset was detected only without a path or with `--preset`; it is now detected on every
  run, and its line is shown on every run, and a preset may now turn rules on.
- **Not chosen:** detecting `:word` per message (false placeholders in other libraries' text, e.g. `Ratio:high`, and
  no way to tell a pipe plural); a `--placeholders laravel` flag (the person would have to know it).
