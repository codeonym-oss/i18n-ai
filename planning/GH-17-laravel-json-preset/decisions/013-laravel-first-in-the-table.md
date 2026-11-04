# 013: Laravel's row comes first in the preset table

**Date:** 2026-10-23 (ticket pass, Q7; agreed: "ok", to the recommended option 1)

**Question:** an Inertia app has `laravel/framework` in `composer.json` and vue-i18n or i18next in `package.json`,
whose usual places include `lang`; which preset wins with no path given?

**Decision:** **Laravel's row is first.** A frontend library's tree elsewhere is reached by naming its path, and
keeps today's rules there (decision 007).

- **Why:** `laravel/framework` is an unambiguous signal, and `lang/` is Laravel's directory.
- **Not chosen:** last (Laravel's own `lang/` read as vue-i18n's, its `:name` and pipes unchecked).
