# 008: A message syntax, set on the preset row and carried to the rules

**Date:** 2026-10-23 (ticket pass, Q2; agreed: "ok", to the recommended option 1)

**Question:** how does "Laravel's syntax is on" reach the scanner (keys as the source), the schema (`:name`, pipes)
and the prompt?

**Decision:** **a domain enum `MessageSyntax` (`STANDARD`, `LARAVEL`), a field of `Preset` (`syntax`), copied by
`with_preset` onto `TreeRequest` when decision 007's condition holds, then onto `LocaleTree` and `LocaleSchema`.**
`signature_of`, `check` and the prompts read it from the schema; the scanner from the request.

- **Why:** the preset table stays the one place a library is described; the scan and the generation already share
  `TreeRequest` → `LocaleTree` → `extract_schema`.
- **Not chosen:** a `laravel: bool` (a library's name in generic types); three separate flags (combinations no
  library uses).
