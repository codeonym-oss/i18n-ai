# 002: Pipe plurals are parsed, with Laravel's own form counts

**Superseded by 010** (in part: which messages are pipe plurals).

**Date:** 2026-10-23 (grilling, Q2; agreed: "ok, 1")

**Question:** how are Laravel's `trans_choice` plurals (`one|many`, `{0} none|[1,19] some|[20,*] many`) translated
and checked?

**Decision:** **they are parsed.** Forms without a range get the target language's number of forms, each described
to the model by the counts it is used for; forms with an explicit range (`{n}`, `[a,b]`, `[a,*]`) keep their ranges
as written, only their text translated. The rule checks the number of forms and the ranges.

The number of forms and what each index means come from **Laravel's own table** (`MessageSelector::getPluralIndex`,
from Symfony's old pluralization rules), copied into the domain as data, not from CLDR: Laravel gives French 2 forms
where CLDR's gettext rule gives 3.

- **Why:** plural strings are where a wrong shape breaks a Laravel app at runtime (an index with no form); only
  parsing is correct for languages with more forms than English.
- **Not chosen:** keeping the source's shape (wrong for Russian, Arabic…); leaving pipe messages untranslated
  (safe, but nothing done). CLDR's counts were first proposed for the form count and corrected before writing:
  Laravel does not read CLDR.
